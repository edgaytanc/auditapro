"""
Servicio de validación de Work Paper Numbers.

Valida que los números de papel de trabajo (work_paper_number) en las marcas de
auditoría coincidan con archivos de plantilla reales.
"""

import re
import logging
from difflib import SequenceMatcher
from auditoria.config.exclusion_rules import is_excluded
from auditoria.services.template_file_registry import TemplateFileRegistry

logger = logging.getLogger(__name__)


class ValidationResult:
    """Resultado de la validación de un work paper number"""

    def __init__(self, work_paper_input):
        self.work_paper_input = work_paper_input
        self.is_valid = False
        self.normalized_name = ''
        self.matched_files = []
        self.is_excluded = False
        self.exclusion_reason = None
        self.exclusion_severity = None
        self.suggestions = []
        self.error_message = None

    def to_dict(self):
        """Convierte el resultado a diccionario"""
        return {
            'work_paper_input': self.work_paper_input,
            'is_valid': self.is_valid,
            'normalized_name': self.normalized_name,
            'matched_files': [
                {
                    'filename': f.filename,
                    'display_name': f.display_name,
                    'folder': f.folder
                }
                for f in self.matched_files
            ],
            'is_excluded': self.is_excluded,
            'exclusion_reason': self.exclusion_reason,
            'exclusion_severity': self.exclusion_severity,
            'suggestions': self.suggestions,
            'error_message': self.error_message
        }

    def __repr__(self):
        status = "VALID" if self.is_valid else "EXCLUDED" if self.is_excluded else "INVALID"
        return f"<ValidationResult: {self.work_paper_input} - {status}>"


class WorkPaperValidator:
    """
    Validador de work paper numbers contra archivos de plantilla reales.
    """

    def __init__(self, use_cache=True):
        """
        Inicializa el validador.

        Args:
            use_cache (bool): Si True, usa caché para el registro de plantillas
        """
        self.registry = TemplateFileRegistry(use_cache=use_cache)
        logger.info(f"WorkPaperValidator inicializado con {len(self.registry)} archivos")

    def normalize_text(self, text):
        """
        Normaliza texto para matching (mismo método que AuditMarkProcessor).

        Args:
            text (str): Texto a normalizar

        Returns:
            str: Texto normalizado
        """
        if not text:
            return ''

        # Paso 1: Eliminar números iniciales (incluyendo decimales) y espacios
        # Ejemplos: "2 " → "", "4.1 " → "", "10 " → ""
        text = re.sub(r'^\d+(\.\d+)?\s*', '', text)

        # Paso 2: Eliminar extensiones
        text = re.sub(r'\.(xlsx|docx|xls|doc|pdf)$', '', text, flags=re.IGNORECASE)

        # Paso 3: Normalización estándar
        text = text.upper()
        text = re.sub(r'[^A-Z0-9]', '', text)

        return text

    def validate_work_paper_name(self, work_paper_input):
        """
        Valida un work paper number contra las plantillas disponibles.

        Args:
            work_paper_input (str): El work paper number a validar

        Returns:
            ValidationResult: Resultado de la validación
        """
        result = ValidationResult(work_paper_input)

        # Validar entrada
        if not work_paper_input or not work_paper_input.strip():
            result.error_message = "Work paper number vacío"
            return result

        work_paper_input = work_paper_input.strip()

        # Verificar si está excluido
        exclusion_info = is_excluded(work_paper_input)
        if exclusion_info['is_excluded']:
            result.is_excluded = True
            result.exclusion_reason = exclusion_info['reason']
            result.exclusion_severity = exclusion_info['severity']
            result.error_message = f"Excluido: {exclusion_info['reason']}"
            return result

        # Normalizar el input
        normalized_input = self.normalize_text(work_paper_input)
        result.normalized_name = normalized_input

        if not normalized_input:
            result.error_message = "Work paper number inválido después de normalización"
            return result

        # Buscar coincidencias
        matched_files = self._find_matches(normalized_input)

        if matched_files:
            result.is_valid = True
            result.matched_files = matched_files
        else:
            result.is_valid = False
            result.error_message = "No se encontró ninguna plantilla coincidente"
            # Generar sugerencias
            result.suggestions = self.suggest_corrections(normalized_input)

        return result

    def _find_matches(self, normalized_input):
        """
        Busca archivos que coincidan con el input normalizado.

        Args:
            normalized_input (str): Input normalizado

        Returns:
            list: Lista de TemplateFile coincidentes
        """
        matched_files = []

        # Obtener archivos no excluidos
        valid_files = self.registry.get_work_paper_files(include_excluded=False)

        for template_file in valid_files:
            normalized_file = template_file.normalized_name

            # Matching bidireccional (substring)
            if normalized_input in normalized_file or normalized_file in normalized_input:
                matched_files.append(template_file)

        return matched_files

    def suggest_corrections(self, normalized_input, max_suggestions=3):
        """
        Genera sugerencias de corrección para un input inválido.

        Usa fuzzy matching (Levenshtein distance) para encontrar las coincidencias
        más cercanas.

        Args:
            normalized_input (str): Input normalizado
            max_suggestions (int): Número máximo de sugerencias

        Returns:
            list: Lista de sugerencias ordenadas por similitud
        """
        if not normalized_input:
            return []

        valid_files = self.registry.get_work_paper_files(include_excluded=False)
        suggestions = []

        for template_file in valid_files:
            normalized_file = template_file.normalized_name

            # Calcular similitud
            similarity = SequenceMatcher(None, normalized_input, normalized_file).ratio()

            suggestions.append({
                'display_name': template_file.display_name,
                'normalized_name': normalized_file,
                'filename': template_file.filename,
                'similarity_score': similarity
            })

        # Ordenar por similitud (de mayor a menor)
        suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)

        # Devolver top N sugerencias
        return suggestions[:max_suggestions]

    def get_valid_work_paper_names(self):
        """
        Obtiene lista de todos los nombres válidos de work papers.

        Returns:
            list: Lista de nombres de visualización
        """
        return self.registry.get_display_names(include_excluded=False)

    def get_valid_normalized_names(self):
        """
        Obtiene lista de todos los nombres normalizados válidos.

        Returns:
            list: Lista de nombres normalizados
        """
        return self.registry.get_normalized_names(include_excluded=False)

    def validate_audit_marks(self, audit_id):
        """
        Valida todos los work paper numbers de una auditoría.

        Args:
            audit_id (int): ID de la auditoría

        Returns:
            dict: Reporte de validación
        """
        from auditoria.models import AuditMark

        marks = AuditMark.objects.filter(audit_id=audit_id, is_active=True)

        results = {
            'audit_id': audit_id,
            'total_marks': marks.count(),
            'valid_marks': 0,
            'invalid_marks': 0,
            'excluded_marks': 0,
            'marks_without_work_paper': 0,
            'details': []
        }

        for mark in marks:
            if not mark.work_paper_number:
                results['marks_without_work_paper'] += 1
                continue

            validation_result = self.validate_work_paper_name(mark.work_paper_number)

            detail = {
                'mark_id': mark.id,
                'symbol': mark.symbol,
                'description': mark.description[:50],  # Primeros 50 caracteres
                'work_paper_number': mark.work_paper_number,
                'validation': validation_result.to_dict()
            }

            results['details'].append(detail)

            if validation_result.is_excluded:
                results['excluded_marks'] += 1
            elif validation_result.is_valid:
                results['valid_marks'] += 1
            else:
                results['invalid_marks'] += 1

        # Calcular tasa de coincidencia
        matchable_marks = results['total_marks'] - results['marks_without_work_paper'] - results['excluded_marks']
        if matchable_marks > 0:
            results['match_rate'] = (results['valid_marks'] / matchable_marks) * 100
        else:
            results['match_rate'] = 0

        return results

    def validate_bulk(self, work_paper_numbers):
        """
        Valida múltiples work paper numbers de una vez.

        Args:
            work_paper_numbers (list): Lista de work paper numbers

        Returns:
            list: Lista de ValidationResult
        """
        results = []

        for wp_number in work_paper_numbers:
            result = self.validate_work_paper_name(wp_number)
            results.append(result)

        return results

    def get_statistics(self):
        """
        Obtiene estadísticas del validador.

        Returns:
            dict: Estadísticas
        """
        registry_stats = self.registry.get_statistics()

        return {
            'registry_stats': registry_stats,
            'validator_status': 'active',
            'using_cache': self.registry.use_cache
        }

    def refresh(self):
        """Refresca el registro de plantillas"""
        logger.info("Refrescando WorkPaperValidator...")
        self.registry.refresh_cache()
        logger.info("WorkPaperValidator actualizado")

    def __repr__(self):
        stats = self.registry.get_statistics()
        return f"<WorkPaperValidator: {stats['valid_files']} valid templates>"
