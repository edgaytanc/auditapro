"""
Servicio para importar marcas de auditoría desde archivos Excel con filtrado por color.
"""

from openpyxl import load_workbook
from django.db import transaction
from django.core.exceptions import ValidationError
from auditoria.models import AuditMark
from auditoria.config.exclusion_rules import is_excluded
import logging
import re

logger = logging.getLogger(__name__)

# Número consecutivo con el que empieza el nombre del papel de trabajo
# ('2 SUMARIA...', '2_CEDULA_SUMARIA...', '4.1 PASIVOS...').
_NUMERO_INICIAL = re.compile(r'^\d+(?:\.\d+)*[\s_\-.]*')
_EXTENSION = re.compile(r'\.(xlsx|docx|xls|doc|pdf)$', re.IGNORECASE)


def canonizar_papel_de_trabajo(texto):
    """
    Deja el nombre del papel de trabajo en la forma que pide la instrucción
    del propio sistema: MAYÚSCULAS, sin el número consecutivo, sin extensión y
    con espacios en lugar de guiones bajos.

        '2_CEDULA_SUMARIA_CAJA_BANCOS.XLSX' → 'CEDULA SUMARIA CAJA BANCOS'
        'sumaria cajas y bancos'            → 'SUMARIA CAJAS Y BANCOS'
        '2 SUMARIA CAJAS Y BANCOS.xlsx'     → 'SUMARIA CAJAS Y BANCOS'

    Antes esto lo tenía que hacer a mano el usuario y, si no lo hacía, la carga
    mostraba una advertencia. Ahora lo aplica el sistema.
    """
    if not texto:
        return texto

    nombre = _EXTENSION.sub('', str(texto).strip())
    sin_numero = _NUMERO_INICIAL.sub('', nombre)

    # Un nombre que solo era el número consecutivo se deja como venía.
    if sin_numero.strip(' _-.'):
        nombre = sin_numero

    nombre = nombre.replace('_', ' ')
    return ' '.join(nombre.split()).upper()


class AuditMarkImportService:
    """Servicio para importar marcas de auditoría desde Excel con filtrado de color."""

    GREEN_COLORS = [
        '00FF00', 'C6EFCE', '90EE90', '92D050', 'C5E0B4',
        '00B050', 'E2EFDA', 'A9D08E', '70AD47'
    ]
    YELLOW_COLORS = [
        'FFFF00', 'FFFFE0', 'FFF4CE', 'FFEB9C', 'FFD966',
        'FFC000', 'F4B084', 'FCE4D6'
    ]

    def __init__(self, audit_id, excel_file):
        self.audit_id = audit_id
        self.excel_file = excel_file
        self.marks_imported = 0
        self.marks_skipped_white = 0
        self.marks_skipped_yellow = 0
        self.marks_skipped_invalid = 0
        self.marks_corrected = 0
        self.errors = []
        self.avisos = []
        self._validador = None

    @property
    def validador(self):
        """Validador contra las plantillas reales (se construye una sola vez)."""
        if self._validador is None:
            from auditoria.services.work_paper_validator import WorkPaperValidator
            self._validador = WorkPaperValidator()
        return self._validador

    def validate_file(self):
        """Valida el archivo Excel cargado."""
        filename = self.excel_file.name.lower()
        if not (filename.endswith('.xlsx') or filename.endswith('.xls')):
            raise ValidationError("El archivo debe ser formato Excel (.xlsx o .xls)")

        if self.excel_file.size > 5 * 1024 * 1024:
            raise ValidationError("El archivo no debe superar 5MB")

        try:
            wb = load_workbook(self.excel_file, read_only=True)
            wb.close()
        except Exception as e:
            raise ValidationError(f"El archivo está corrupto o no se puede leer: {str(e)}")

    def _get_cell_background_color(self, cell):
        """Extrae el color de fondo de la celda."""
        if cell.fill and cell.fill.start_color:
            color = cell.fill.start_color
            if hasattr(color, 'rgb') and color.rgb:
                rgb = str(color.rgb)
                if len(rgb) == 8:
                    return rgb[2:].upper()
                return rgb.upper()
        return None

    def _is_green_row(self, row_cells):
        """Verifica si la fila tiene fondo verde."""
        for cell in row_cells:
            bg_color = self._get_cell_background_color(cell)
            if bg_color and any(green in bg_color for green in self.GREEN_COLORS):
                return True
        return False

    def _is_yellow_row(self, row_cells):
        """Verifica si la fila tiene fondo amarillo."""
        for cell in row_cells:
            bg_color = self._get_cell_background_color(cell)
            if bg_color and any(yellow in bg_color for yellow in self.YELLOW_COLORS):
                return True
        return False

    def parse_excel(self):
        """Analiza el archivo Excel y extrae las marcas."""
        wb = load_workbook(self.excel_file, data_only=True)
        ws = wb.active
        marks = []

        for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), start=2):
            try:
                if self._is_yellow_row(row_cells):
                    self.marks_skipped_yellow += 1
                    continue

                if self._is_green_row(row_cells):
                    mark_data = self._extract_mark_from_row(row_cells, row_idx)
                    if mark_data:
                        marks.append(mark_data)
                    else:
                        self.marks_skipped_invalid += 1
                else:
                    has_data = any(cell.value for cell in row_cells[:4])
                    if has_data:
                        self.marks_skipped_white += 1

            except Exception as e:
                self.errors.append(f"Fila {row_idx}: Error - {str(e)}")
                self.marks_skipped_invalid += 1

        wb.close()
        return marks

    def _extract_mark_from_row(self, row_cells, row_idx):
        """Extrae datos de marca de una fila (3 columnas)."""
        symbol = str(row_cells[0].value).strip() if row_cells[0].value else None
        description = str(row_cells[1].value).strip() if row_cells[1].value else None
        work_paper = str(row_cells[2].value).strip() if len(row_cells) > 2 and row_cells[2].value else None

        if not symbol or not description:
            return None

        if description and ("Ejemplo:" in description or "Example:" in description):
            return None

        if work_paper:
            work_paper = self._papel_de_trabajo_canonico(work_paper, row_idx)

        return {
            'symbol': symbol,
            'description': description,
            'work_paper_number': work_paper
        }

    def _papel_de_trabajo_canonico(self, work_paper, row_idx):
        """
        Aplica la instrucción del sistema al nombre del papel de trabajo y
        avisa —sin bloquear la carga— si no corresponde a ninguna plantilla.
        """
        canonico = canonizar_papel_de_trabajo(work_paper)

        if canonico != work_paper:
            self.marks_corrected += 1
            self.avisos.append(
                f"Fila {row_idx}: '{work_paper}' se guardó como '{canonico}', "
                f"según la instrucción de la pantalla."
            )

        if not self._existe_plantilla(canonico):
            sugerencia = self._sugerencia_para(canonico)
            detalle = f" ¿Quiso decir '{sugerencia}'?" if sugerencia else ''
            self.errors.append(
                f"Fila {row_idx}: '{canonico}' no corresponde a ninguna "
                f"plantilla del sistema.{detalle} La marca se importó igual, "
                f"pero no se pegará en ningún papel de trabajo."
            )

        return canonico

    def _existe_plantilla(self, work_paper):
        """
        True si el nombre llega a pegarse en alguna plantilla real.

        Se usa el MISMO criterio con el que después se pegan las marcas
        (`nombres_coinciden`), no el del validador —que es más permisivo—, para
        que el aviso no diga lo contrario de lo que va a pasar.
        """
        from auditoria.services.audit_mark_processor import nombres_coinciden

        try:
            if is_excluded(work_paper)['is_excluded']:
                return True
            normalizado = self.validador.normalize_text(work_paper)
            return any(
                nombres_coinciden(normalizado, plantilla.normalized_name)
                for plantilla in self.validador.registry.get_work_paper_files()
            )
        except Exception as e:
            # Un fallo al leer el árbol de plantillas no debe tumbar la carga.
            logger.warning("No se pudo validar '%s': %s", work_paper, e)
            return True

    def _sugerencia_para(self, work_paper):
        """Nombre de plantilla más parecido, si hay uno razonablemente cercano."""
        try:
            normalizado = self.validador.normalize_text(work_paper)
            sugerencias = self.validador.suggest_corrections(normalizado, max_suggestions=1)
        except Exception:
            return None
        if sugerencias and sugerencias[0]['similarity_score'] >= 0.6:
            # Se sugiere ya en la forma que pide la instrucción, no el nombre
            # crudo del archivo ('_CEDULA_SUMARIA_CAJA_BANCOS').
            return canonizar_papel_de_trabajo(sugerencias[0]['filename'])
        return None

    @transaction.atomic
    def import_marks(self, replace_existing=True):
        """Importa marcas a la base de datos."""
        self.validate_file()
        marks = self.parse_excel()

        if replace_existing:
            AuditMark.objects.filter(audit_id=self.audit_id).delete()

        if marks:
            mark_objects = [
                AuditMark(
                    audit_id=self.audit_id,
                    symbol=mark['symbol'],
                    description=mark['description'],
                    work_paper_number=mark['work_paper_number'],
                    is_active=True
                )
                for mark in marks
            ]
            AuditMark.objects.bulk_create(mark_objects)
            self.marks_imported = len(mark_objects)

        return {
            'success': True,
            'marks_imported': self.marks_imported,
            'marks_skipped_white': self.marks_skipped_white,
            'marks_skipped_yellow': self.marks_skipped_yellow,
            'marks_skipped_invalid': self.marks_skipped_invalid,
            'marks_corrected': self.marks_corrected,
            'avisos': self.avisos,
            'errors': self.errors
        }
