"""
Tests comprehensivos para el sistema de validación de Work Papers.

Prueba todas las funcionalidades:
- Reglas de exclusión
- TemplateFileRegistry
- WorkPaperValidator
- AuditMarkProcessor con lógica de exclusión
- Normalización de nombres
"""

import os
import tempfile
from datetime import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from audits.models import Audit
from users.models import Roles
from auditoria.models import AuditMark, WorkPaperValidationLog
from auditoria.config.exclusion_rules import (
    is_excluded,
    check_keyword_exclusion,
    check_prefix_exclusion,
    check_extension_exclusion
)
from auditoria.services.template_file_registry import (
    TemplateFileRegistry,
    TemplateFile
)
from auditoria.services.work_paper_validator import (
    WorkPaperValidator,
    ValidationResult
)
from auditoria.services.audit_mark_processor import AuditMarkProcessor

User = get_user_model()


class ExclusionRulesTestCase(TestCase):
    """Test de reglas de exclusión"""

    def test_keyword_exclusion_programa(self):
        """PROGRAMA debe ser excluido"""
        result = is_excluded("PROGRAMA AUDITORIA")
        self.assertTrue(result['is_excluded'])
        self.assertEqual(result['rule_type'], 'keyword')
        self.assertIn('hipervínculos', result['reason'].lower())

    def test_keyword_exclusion_plantilla(self):
        """plantilla debe ser excluido"""
        result = is_excluded("plantilla_marcas_auditoria.xlsx")
        self.assertTrue(result['is_excluded'])
        self.assertEqual(result['rule_type'], 'keyword')

    def test_prefix_exclusion_temp_file(self):
        """Archivos temporales de Excel deben ser excluidos"""
        # Actualizado árbol 2026
        result = is_excluded("~$2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx")
        self.assertTrue(result['is_excluded'])
        self.assertEqual(result['rule_type'], 'prefix')

    def test_extension_exclusion_backup(self):
        """Archivos .bak deben ser excluidos"""
        # Actualizado árbol 2026
        result = is_excluded("CEDULA_SUMARIA_CAJA_BANCOS.bak")
        self.assertTrue(result['is_excluded'])
        self.assertEqual(result['rule_type'], 'extension')

    def test_no_exclusion_valid_file(self):
        """Archivos válidos no deben ser excluidos"""
        # Actualizado árbol 2026
        result = is_excluded("CEDULA SUMARIA CAJA BANCOS")
        self.assertFalse(result['is_excluded'])
        self.assertIsNone(result['rule_type'])

    def test_case_insensitive_keyword(self):
        """Keywords deben ser case-insensitive"""
        result1 = is_excluded("PROGRAMA")
        result2 = is_excluded("programa")
        result3 = is_excluded("Programa")

        self.assertTrue(result1['is_excluded'])
        self.assertTrue(result2['is_excluded'])
        self.assertTrue(result3['is_excluded'])


class NormalizationTestCase(TestCase):
    """Test de normalización de nombres"""

    def setUp(self):
        self.processor = AuditMarkProcessor(audit_id=1, filename="dummy.xlsx")

    def test_normalize_sumaria_with_number(self):
        """Test: '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx' → 'CEDULASUMARIACAJABANCOS'"""
        # Actualizado árbol 2026
        result = self.processor.normalize_text("2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx")
        self.assertEqual(result, "CEDULASUMARIACAJABANCOS")

    def test_normalize_sumaria_without_number(self):
        """Test: 'CEDULA SUMARIA CAJA BANCOS' → 'CEDULASUMARIACAJABANCOS'"""
        # Actualizado árbol 2026
        result = self.processor.normalize_text("CEDULA SUMARIA CAJA BANCOS")
        self.assertEqual(result, "CEDULASUMARIACAJABANCOS")

    def test_normalize_with_extension_only(self):
        """Test: 'CEDULA_SUMARIA_CAJA_BANCOS.xlsx' → 'CEDULASUMARIACAJABANCOS'"""
        # Actualizado árbol 2026
        result = self.processor.normalize_text("CEDULA_SUMARIA_CAJA_BANCOS.xlsx")
        self.assertEqual(result, "CEDULASUMARIACAJABANCOS")

    def test_normalize_different_extensions(self):
        """Test normalización con diferentes extensiones"""
        # Actualizado árbol 2026
        inputs = [
            "10_INTEGRACION_EGRESOS.docx",
            "10_INTEGRACION_EGRESOS.xlsx",
            "10_INTEGRACION_EGRESOS.xls",
            "10_INTEGRACION_EGRESOS"
        ]
        expected = "INTEGRACIONEGRESOS"

        for inp in inputs:
            result = self.processor.normalize_text(inp)
            self.assertEqual(result, expected, f"Failed for input: {inp}")

    def test_normalize_preserves_letters(self):
        """Test: Las letras iniciales deben preservarse"""
        result1 = self.processor.normalize_text("A 1 Balance.docx")
        self.assertTrue(result1.startswith('A'))

        result2 = self.processor.normalize_text("B-10")
        self.assertTrue(result2.startswith('B'))

    def test_normalize_removes_special_chars(self):
        """Test: Los caracteres especiales deben eliminarse"""
        # Actualizado árbol 2026
        result = self.processor.normalize_text("CEDULA - SUMARIA & CAJA BANCOS")
        # El "&" y el "-" se eliminan correctamente
        self.assertEqual(result, "CEDULASUMARIACAJABANCOS")

    def test_three_formats_match(self):
        """Test: Los tres formatos del usuario deben coincidir"""
        # Actualizado árbol 2026
        format1 = self.processor.normalize_text("2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx")
        format2 = self.processor.normalize_text("CEDULA SUMARIA CAJA BANCOS")
        format3 = self.processor.normalize_text("CEDULA_SUMARIA_CAJA_BANCOS.xlsx")

        self.assertEqual(format1, format2)
        self.assertEqual(format2, format3)
        self.assertEqual(format1, "CEDULASUMARIACAJABANCOS")


class AuditMarkProcessorTestCase(TestCase):
    """Test del AuditMarkProcessor con lógica de exclusión"""

    def setUp(self):
        # Crear role y usuario de prueba
        self.role = Roles.objects.create(name="audit_manager", verbose_name="Audit Manager")
        self.user = User.objects.create_user(
            username="test_auditor",
            email="test@example.com",
            password="testpass123",
            role=self.role
        )
        # Crear auditoría de prueba
        self.audit = Audit.objects.create(
            title="Test Audit 2025",
            identidad="TEST-2025",
            fechaInit=timezone.now(),
            fechaEnd=timezone.now(),
            tipoAuditoria="F",
            audit_manager=self.user
        )

    def test_should_process_file_valid(self):
        """Archivos válidos deben ser procesados"""
        # Actualizado árbol 2026
        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx"
        )
        should_process, reason = processor.should_process_file()
        self.assertTrue(should_process)
        self.assertIsNone(reason)

    def test_should_process_file_programa_excluded(self):
        """Archivos PROGRAMA deben ser excluidos"""
        # Actualizado árbol 2026
        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="1_PROGRAMA_AUDITORIA_CAJA_BANCOS.xlsx"
        )
        should_process, reason = processor.should_process_file()
        self.assertFalse(should_process)
        self.assertIsNotNone(reason)
        self.assertIn('hipervínculo', reason.lower())

    def test_should_process_file_temp_excluded(self):
        """Archivos temporales deben ser excluidos"""
        # Actualizado árbol 2026
        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="~$2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx"
        )
        should_process, reason = processor.should_process_file()
        self.assertFalse(should_process)
        self.assertIsNotNone(reason)

    def test_mark_excluded_by_work_paper(self):
        """Marcas con work_paper_number excluido deben ser detectadas"""
        mark = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="PROGRAMA"
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="test.docx"
        )

        is_excl, reason = processor._is_mark_excluded(mark)
        self.assertTrue(is_excl)
        self.assertIsNotNone(reason)

    def test_mark_not_excluded_valid(self):
        """Marcas válidas no deben ser excluidas"""
        # Actualizado árbol 2026
        mark = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="CEDULA SUMARIA CAJA BANCOS"
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="test.docx"
        )

        is_excl, reason = processor._is_mark_excluded(mark)
        self.assertFalse(is_excl)
        self.assertIsNone(reason)

    def test_get_matching_marks_excludes_programa(self):
        """get_matching_marks debe excluir marcas PROGRAMA"""
        # Actualizado árbol 2026
        # Crear marca válida
        mark1 = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Valid mark",
            work_paper_number="CEDULA SUMARIA CAJA BANCOS"
        )

        # Crear marca PROGRAMA (debe ser excluida)
        mark2 = AuditMark.objects.create(
            audit=self.audit,
            symbol="◊",
            description="Programa mark",
            work_paper_number="PROGRAMA"
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx"
        )

        matched_marks = processor.get_matching_marks()

        # Solo la marca válida debe coincidir
        self.assertEqual(len(matched_marks), 1)
        self.assertEqual(matched_marks[0].id, mark1.id)

    def test_exact_matching(self):
        """Test matching exacto: work paper y archivo normalizan igual"""
        # Actualizado árbol 2026
        mark = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="CEDULA SUMARIA CAJA BANCOS"
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx"
        )

        matched_marks = processor.get_matching_marks()

        # "CEDULASUMARIACAJABANCOS" == "CEDULASUMARIACAJABANCOS"
        self.assertEqual(len(matched_marks), 1)
        self.assertEqual(matched_marks[0].id, mark.id)

    def test_bidirectional_matching(self):
        """Test matching bidireccional (contención con ratio >= 0.8)"""
        # Actualizado árbol 2026: la contención exige ratio de longitud >= 0.8
        mark = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="CONCILIACION"  # Substring más corto (singular)
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="3_CONCILIACIONES.xlsx"  # Nombre completo
        )

        matched_marks = processor.get_matching_marks()

        # Debe coincidir: "CONCILIACION" está en "CONCILIACIONES" (ratio 12/14 >= 0.8)
        self.assertEqual(len(matched_marks), 1)
        self.assertEqual(matched_marks[0].id, mark.id)

    def test_bidirectional_matching_reverse(self):
        """Test matching bidireccional (reverso, contención con ratio >= 0.8)"""
        # Actualizado árbol 2026: la contención exige ratio de longitud >= 0.8
        mark = AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="ARQUEO DE CAJAS"  # Nombre completo (plural)
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="5_ARQUEO_DE_CAJA.xlsx"  # Substring más corto
        )

        matched_marks = processor.get_matching_marks()

        # Debe coincidir: "ARQUEODECAJA" está en "ARQUEODECAJAS" (ratio 12/13 >= 0.8)
        self.assertEqual(len(matched_marks), 1)

    def test_short_substring_does_not_match(self):
        """Test: substrings demasiado cortos NO deben coincidir (ratio < 0.8)"""
        # Actualizado árbol 2026: evita falsos positivos con nombres genéricos
        AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Test mark",
            work_paper_number="SUMARIA"  # Substring muy corto
        )

        processor = AuditMarkProcessor(
            audit_id=self.audit.id,
            filename="2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx"
        )

        matched_marks = processor.get_matching_marks()

        # "SUMARIA" está contenido pero ratio 7/23 < 0.8 → no coincide
        self.assertEqual(len(matched_marks), 0)


class TemplateFileTestCase(TestCase):
    """Test de TemplateFile class"""

    def test_template_file_normalization(self):
        """Test normalización en TemplateFile"""
        # Actualizado árbol 2026
        template_file = TemplateFile(
            filename="4 CONFIRMACIONES.xlsx",
            folder="4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS",
            full_path="/test/path.xlsx",
            is_internal=False
        )

        self.assertEqual(template_file.normalized_name, "CONFIRMACIONES")
        self.assertEqual(template_file.display_name, "CONFIRMACIONES")
        self.assertEqual(template_file.file_type, "xlsx")

    def test_template_file_normalization_underscores(self):
        """Test normalización con nombres con guiones bajos del árbol 2026"""
        # Actualizado árbol 2026: los archivos nuevos usan guiones bajos
        template_file = TemplateFile(
            filename="2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx",
            folder="4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS",
            full_path="/test/path2.xlsx",
            is_internal=False
        )

        self.assertEqual(template_file.normalized_name, "CEDULASUMARIACAJABANCOS")
        self.assertEqual(template_file.file_type, "xlsx")

    def test_template_file_exclusion_detection(self):
        """TemplateFile debe detectar archivos excluidos"""
        # Actualizado árbol 2026
        template_file = TemplateFile(
            filename="1_PROGRAMA_AUDITORIA_CAJA_BANCOS.xlsx",
            folder="4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS",
            full_path="/test/programa.xlsx",
            is_internal=False
        )

        self.assertTrue(template_file.is_excluded)
        self.assertIn('hipervínculo', template_file.exclusion_info['reason'].lower())

    def test_template_file_to_dict(self):
        """Test conversión a diccionario"""
        template_file = TemplateFile(
            filename="test.xlsx",
            folder="4 PRUEBAS SUSTANTIVAS",
            full_path="/test/test.xlsx",
            is_internal=False
        )

        result = template_file.to_dict()

        self.assertIn('filename', result)
        self.assertIn('normalized_name', result)
        self.assertIn('display_name', result)
        self.assertIn('is_excluded', result)


class WorkPaperValidatorIntegrationTestCase(TestCase):
    """Tests de integración para WorkPaperValidator"""

    def setUp(self):
        # Crear role, usuario y auditoría de prueba
        self.role = Roles.objects.create(name="audit_manager", verbose_name="Audit Manager")
        self.user = User.objects.create_user(
            username="test_auditor",
            email="test@example.com",
            password="testpass123",
            role=self.role
        )
        self.audit = Audit.objects.create(
            title="Test Audit 2025",
            identidad="TEST-2025",
            fechaInit=timezone.now(),
            fechaEnd=timezone.now(),
            tipoAuditoria="F",
            audit_manager=self.user
        )

    def test_validator_initialization(self):
        """Test inicialización del validador"""
        validator = WorkPaperValidator(use_cache=False)
        self.assertIsNotNone(validator.registry)
        self.assertGreater(len(validator.registry), 0)

    def test_validate_valid_work_paper(self):
        """Test validación de work paper válido"""
        validator = WorkPaperValidator(use_cache=False)

        # Actualizado árbol 2026: coincide con
        # '4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS/2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'
        result = validator.validate_work_paper_name("CEDULA SUMARIA CAJA BANCOS")

        self.assertIsNotNone(result)
        self.assertTrue(result.is_valid)
        self.assertGreaterEqual(len(result.matched_files), 1)

    def test_validate_excluded_work_paper(self):
        """Test validación de work paper excluido"""
        validator = WorkPaperValidator(use_cache=False)

        result = validator.validate_work_paper_name("PROGRAMA")

        self.assertTrue(result.is_excluded)
        self.assertIsNotNone(result.exclusion_reason)

    def test_validate_empty_work_paper(self):
        """Test validación de work paper vacío"""
        validator = WorkPaperValidator(use_cache=False)

        result = validator.validate_work_paper_name("")

        self.assertFalse(result.is_valid)
        self.assertIn('vacío', result.error_message.lower())

    def test_validate_audit_marks(self):
        """Test validación de todas las marcas de una auditoría"""
        # Crear marcas de prueba
        # Actualizado árbol 2026
        AuditMark.objects.create(
            audit=self.audit,
            symbol="✓",
            description="Valid mark",
            work_paper_number="CEDULA SUMARIA CAJA BANCOS"
        )
        AuditMark.objects.create(
            audit=self.audit,
            symbol="◊",
            description="Excluded mark",
            work_paper_number="PROGRAMA"
        )
        AuditMark.objects.create(
            audit=self.audit,
            symbol="★",
            description="Mark without WP"
            # No work_paper_number
        )

        validator = WorkPaperValidator(use_cache=False)
        report = validator.validate_audit_marks(self.audit.id)

        self.assertEqual(report['total_marks'], 3)
        self.assertEqual(report['marks_without_work_paper'], 1)
        self.assertEqual(report['excluded_marks'], 1)
        # Actualizado árbol 2026: la cédula sumaria existe en el árbol nuevo
        self.assertEqual(report['valid_marks'], 1)

    def test_normalize_consistency(self):
        """Test consistencia de normalización entre Validator y Processor"""
        validator = WorkPaperValidator(use_cache=False)
        processor = AuditMarkProcessor(audit_id=1, filename="dummy.xlsx")

        # Actualizado árbol 2026
        test_strings = [
            "2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx",
            "CEDULA SUMARIA CAJA BANCOS",
            "10_INTEGRACION_EGRESOS.xlsx",
            "A-1"
        ]

        for test_str in test_strings:
            validator_result = validator.normalize_text(test_str)
            processor_result = processor.normalize_text(test_str)

            self.assertEqual(
                validator_result,
                processor_result,
                f"Normalization mismatch for: {test_str}"
            )


class ValidationResultTestCase(TestCase):
    """Test de ValidationResult class"""

    def test_validation_result_to_dict(self):
        """Test conversión de ValidationResult a diccionario"""
        # Actualizado árbol 2026
        result = ValidationResult("CEDULA SUMARIA CAJA BANCOS")
        result.is_valid = True
        result.normalized_name = "CEDULASUMARIACAJABANCOS"

        result_dict = result.to_dict()

        self.assertEqual(result_dict['work_paper_input'], "CEDULA SUMARIA CAJA BANCOS")
        self.assertTrue(result_dict['is_valid'])
        self.assertEqual(result_dict['normalized_name'], "CEDULASUMARIACAJABANCOS")


def run_comprehensive_tests():
    """
    Función helper para ejecutar todos los tests con output detallado.

    Uso:
        python manage.py shell
        >>> from auditoria.tests.test_workpaper_validation import run_comprehensive_tests
        >>> run_comprehensive_tests()
    """
    import unittest

    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Agregar todos los test cases
    suite.addTests(loader.loadTestsFromTestCase(ExclusionRulesTestCase))
    suite.addTests(loader.loadTestsFromTestCase(NormalizationTestCase))
    suite.addTests(loader.loadTestsFromTestCase(AuditMarkProcessorTestCase))
    suite.addTests(loader.loadTestsFromTestCase(TemplateFileTestCase))
    suite.addTests(loader.loadTestsFromTestCase(WorkPaperValidatorIntegrationTestCase))
    suite.addTests(loader.loadTestsFromTestCase(ValidationResultTestCase))

    # Ejecutar tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result
