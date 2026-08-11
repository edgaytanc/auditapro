"""
Informe de diagnóstico técnico del cliente (5 de agosto de 2026):
«las referencias no se pegan cuando se agregan Marcas y Datos auditor y fecha»,
«la referencia permanece estática», «en 1 PROGRAMA_DE_AUDITORIA_ACTIVOS_FIJOS
la referencia sí se pegó, pero las marcas no».

El informe atribuía el fallo a la capa de mapeo de identificadores. La causa
real resultó ser otra y es la misma en los tres síntomas: **escrituras sobre
celdas combinadas**. openpyxl lanza «'MergedCell' object attribute 'value' is
read-only»; el error se tragaba con un warning (marcas) o devolvía HTTP 500
(datos del auditor), y de ahí que fallara en unas plantillas sí y en otras no.

A eso se suman:
  · la referencia solo se escribía si la celda estaba vacía, y la plantilla
    trae un valor de muestra → «la referencia no cambia»;
  · el recuadro se buscaba solo en las 15 primeras columnas, y en varias
    plantillas está en la 16;
  · 'PROGRAMA' excluía también los .xlsx pese a declarar `applies_to`;
  · había tres normalizaciones de nombre distintas.
"""
import os

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from audits.models import Audit
from auditoria.config.exclusion_rules import is_excluded
from auditoria.models import AuditMark
from auditoria.services.audit_mark_processor import AuditMarkProcessor
from auditoria.services.nombres_papeles import normalizar_nombre_papel
from auditoria.services.referencias import inyectar_ref_propia
from auditoria.services.template_file_registry import TemplateFile
from auditoria.services.work_paper_validator import WorkPaperValidator
from django.contrib.auth import get_user_model
from users.models import Roles

Usuario = get_user_model()


def _libro(filas, combinar=()):
    """Libro de una hoja con *filas* y los rangos combinados indicados."""
    libro = Workbook()
    hoja = libro.active
    for fila in filas:
        hoja.append(fila)
    for rango in combinar:
        hoja.merge_cells(rango)
    return libro


def _textos(hoja, filas=60, cols=40):
    return [
        str(hoja.cell(row=f, column=c).value)
        for f in range(1, min(hoja.max_row or 1, filas) + 1)
        for c in range(1, min(hoja.max_column or 1, cols) + 1)
        if hoja.cell(row=f, column=c).value not in (None, '')
    ]


class ReferenciaSeActualiza(SimpleTestCase):
    """Img. 3 y 4: la referencia permanecía estática dentro de la plantilla."""

    def test_sustituye_la_referencia_de_muestra(self):
        libro = _libro([['Ref.', 'A-9']])
        inyectar_ref_propia(libro, '2.2')
        self.assertEqual(libro.active['B1'].value, '2.2')

    def test_rellena_el_hueco_de_la_etiqueta(self):
        libro = _libro([['Ref.   XXXXXX']])
        inyectar_ref_propia(libro, '6.3')
        self.assertEqual(libro.active['A1'].value, 'Ref.   6.3')

    def test_encuentra_el_recuadro_mas_alla_de_la_columna_15(self):
        """'Ref.   XXXXXX' vive en P2 (columna 16) en varias plantillas."""
        hoja_filas = [[None] * 15 + ['Ref.   XXXXXX']]
        libro = _libro(hoja_filas)
        inyectar_ref_propia(libro, '6.1')
        self.assertEqual(libro.active['P1'].value, 'Ref.   6.1')

    def test_no_pisa_el_encabezado_de_la_columna_de_al_lado(self):
        """'REF' como encabezado de tabla no es el recuadro del papel."""
        libro = _libro([['REF', 'PROCEDIMIENTO', 'NIA']])
        inyectar_ref_propia(libro, '9.9')
        self.assertEqual(libro.active['B1'].value, 'PROCEDIMIENTO')

    def test_crea_el_recuadro_si_la_plantilla_no_lo_trae(self):
        libro = _libro([['PROGRAMA DE AUDITORÍA'], ['Dato', 'Valor']])
        inyectar_ref_propia(libro, '3.7')
        self.assertIn('3.7', _textos(libro.active))

    def test_no_confunde_una_nia_con_la_referencia(self):
        libro = _libro([['Ref.', 'NIA-530']])
        inyectar_ref_propia(libro, '1.1')
        self.assertEqual(libro.active['B1'].value, 'NIA-530')


class MarcasEnCeldasCombinadas(TestCase):
    """Img. 8: la marca no se pegaba y el error se tragaba con un warning."""

    def setUp(self):
        rol, _ = Roles.objects.get_or_create(
            name='audit_manager', defaults={'verbose_name': 'Jefe'})
        self.jefe = Usuario.objects.create_user(
            username='jefe_diag', email='jefe_diag@auditapro.test',
            password='Clave.2026', role=rol, plan='A')
        self.auditoria = Audit.objects.create(
            title='QA', identidad='Cliente', tipoAuditoria='F', moneda='GTQ',
            audit_manager=self.jefe, fechaInit='2025-01-01', fechaEnd='2025-12-31')
        AuditMark.objects.create(
            audit=self.auditoria, symbol='✓', description='Verificado',
            work_paper_number='ANALISIS TENDENCIAS INGRESOS', is_active=True)

    def test_el_pie_combinado_no_impide_las_marcas(self):
        """El pie 'A4:D7' cubría la fila donde se escribía el bloque."""
        libro = _libro(
            [['Cuenta', 'Enero', 'Febrero', 'Total'],
             ['Ventas', 100, 200, 300],
             [None, None, None, None],
             ['Nota al pie que ocupa todo el ancho', None, None, None]],
            combinar=('A4:D7',),
        )
        procesador = AuditMarkProcessor(self.auditoria.id,
                                        '3_ANALISIS_TENDENCIAS_INGRESOS.xlsx')
        procesador.process_excel_document(libro)

        self.assertTrue(
            any('Verificado' in t for t in _textos(libro.active)),
            'la marca no se escribió por culpa del rango combinado')

    def test_todas_las_hojas_reciben_su_marca(self):
        libro = Workbook()
        primera = libro.active
        primera.title = 'Hoja A'
        primera.append(['Dato', 1])
        segunda = libro.create_sheet('Hoja B')
        segunda.append(['Otro dato', 2])

        AuditMarkProcessor(self.auditoria.id,
                           '3_ANALISIS_TENDENCIAS_INGRESOS.xlsx'
                           ).process_excel_document(libro)

        for hoja in libro.worksheets:
            self.assertTrue(any('Verificado' in t for t in _textos(hoja)),
                            f'la hoja {hoja.title} se quedó sin marca')


class ProgramaDeAuditoriaEnExcel(SimpleTestCase):
    """Img. 8: el programa en Excel debe recibir sus marcas."""

    def test_word_sigue_protegido(self):
        self.assertTrue(is_excluded('1_PROGRAMA_DE_AUDITORIA.docx')['is_excluded'])

    def test_excel_ya_no_se_excluye(self):
        self.assertFalse(is_excluded('1_PROGRAMA_DE_AUDITORIA.xlsx')['is_excluded'])

    def test_el_procesador_lo_procesa(self):
        procesador = AuditMarkProcessor(
            1, '1_PROGRAMA_DE_AUDITORIA_ACTIVOS_FIJOS.xlsx')
        self.assertTrue(procesador.should_process_file()[0])


class UnSoloIdentificadorDePapel(SimpleTestCase):
    """Sección 4 del informe: había tres normalizaciones distintas."""

    def test_el_conector_y_no_rompe_la_coincidencia(self):
        """'CUESTIONARIO CAJA Y BANCOS' ↔ '1_Cuestionario_Caja_Bancos.xlsx'."""
        self.assertEqual(
            normalizar_nombre_papel('CUESTIONARIO CAJA Y BANCOS'),
            normalizar_nombre_papel('1_Cuestionario_Caja_Bancos.xlsx'))

    def test_la_letra_inicial_del_papel_se_conserva(self):
        """'A' y 'E' son conectores, pero también referencias: 'A-1', 'E-2'."""
        self.assertTrue(normalizar_nombre_papel('A-1 Arqueo de caja').startswith('A'))
        self.assertTrue(normalizar_nombre_papel('E 2 Depreciacion').startswith('E'))

    def test_las_tildes_no_cambian_el_identificador(self):
        self.assertEqual(normalizar_nombre_papel('ANÁLISIS DE TENDENCIAS'),
                         normalizar_nombre_papel('ANALISIS TENDENCIAS'))

    def test_las_tres_capas_normalizan_igual(self):
        nombre = '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'
        del_registro = TemplateFile(nombre, '', '/x', False).normalized_name
        del_validador = WorkPaperValidator(use_cache=False).normalize_text(nombre)
        del_procesador = AuditMarkProcessor(1, nombre).normalize_text(nombre)
        self.assertEqual(del_registro, del_validador)
        self.assertEqual(del_validador, del_procesador)


class FilasVaciasDelCatalogo(TestCase):
    """Img. 1: 16 filas se contaban como «inválidas» y solo estaban vacías."""

    def setUp(self):
        rol, _ = Roles.objects.get_or_create(
            name='audit_manager', defaults={'verbose_name': 'Jefe'})
        self.jefe = Usuario.objects.create_user(
            username='jefe_cat', email='jefe_cat@auditapro.test',
            password='Clave.2026', role=rol, plan='A')
        self.auditoria = Audit.objects.create(
            title='QA', identidad='Cliente', tipoAuditoria='F', moneda='GTQ',
            audit_manager=self.jefe, fechaInit='2025-01-01', fechaEnd='2025-12-31')

    def test_las_filas_verdes_vacias_no_son_invalidas(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        from auditoria.services.audit_mark_import_service import AuditMarkImportService

        verde = PatternFill(start_color='FFC6EFCE', end_color='FFC6EFCE',
                            fill_type='solid')
        libro = Workbook()
        hoja = libro.active
        hoja.append(['Símbolo', 'Descripción', 'Papel de Trabajo'])
        hoja.append(['✓', 'Verificado', 'CEDULA SUMARIA CAJA BANCOS'])
        hoja.append([None, None, None])          # fila verde vacía del catálogo
        for fila in range(2, 4):
            for columna in range(1, 4):
                hoja.cell(row=fila, column=columna).fill = verde

        memoria = io.BytesIO()
        libro.save(memoria)
        resultado = AuditMarkImportService(
            self.auditoria.id,
            SimpleUploadedFile('M.xlsx', memoria.getvalue())
        ).import_marks(replace_existing=True)

        self.assertEqual(resultado['marks_imported'], 1)
        self.assertEqual(resultado['marks_skipped_invalid'], 0)
        self.assertEqual(resultado['marks_skipped_empty'], 1)


class EncabezadoRotulado(SimpleTestCase):
    """Prioridad 1 del cliente: los encabezados como base."""

    def test_entidad_en_la_celda_de_al_lado(self):
        from auditoria.processors.excel.sheet_processor import (
            _rellenar_etiquetas_de_encabezado,
        )

        libro = _libro([['Entidad Auditada:', None], ['NIT:', None]])
        _rellenar_etiquetas_de_encabezado(libro.active, {'[IDENTIDAD]': 'Walmart'})
        self.assertEqual(libro.active['B1'].value, 'Walmart')

    def test_sustituye_el_hueco_de_la_plantilla(self):
        from auditoria.processors.excel.sheet_processor import (
            _rellenar_etiquetas_de_encabezado,
        )

        libro = _libro([['Cliente:', '[NOMBRE DEL CLIENTE]']])
        _rellenar_etiquetas_de_encabezado(libro.active, {'[IDENTIDAD]': 'Walmart'})
        self.assertEqual(libro.active['B1'].value, 'Walmart')

    def test_no_pisa_un_dato_real(self):
        from auditoria.processors.excel.sheet_processor import (
            _rellenar_etiquetas_de_encabezado,
        )

        libro = _libro([['Cliente:', 'Ya escrito por el auditor']])
        _rellenar_etiquetas_de_encabezado(libro.active, {'[IDENTIDAD]': 'Walmart'})
        self.assertEqual(libro.active['B1'].value, 'Ya escrito por el auditor')
