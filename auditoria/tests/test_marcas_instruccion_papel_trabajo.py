"""
Revisión del cliente (guía «CARGA DE MARCAS Y DATOS AUDITOR O JEFE»):

    «lo único a corregir es que en Marcas debe seguir la instrucción que ya
     está en sistema»

La instrucción de la pantalla pide que el «Papel de Trabajo» se escriba en
MAYÚSCULAS, sin el número consecutivo, sin extensión y sin guiones bajos
('2_CEDULA_SUMARIA_CAJA_BANCOS.XLSX' → 'CEDULA SUMARIA CAJA BANCOS'). Eso lo
tenía que hacer a mano el usuario y, si no lo hacía, la carga le devolvía una
lista de «Advertencias» que no eran errores reales. Ahora la aplica el sistema:

  · el nombre se guarda ya canonizado,
  · las correcciones se informan aparte, en «avisos», no como advertencias,
  · «errors» queda solo para lo que sí es un problema: un nombre que no
    corresponde a ninguna plantilla (con la sugerencia del sistema).
"""
import io
import urllib.parse

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill

from audits.models import Audit
from auditoria.services.audit_mark_import_service import (
    AuditMarkImportService,
    canonizar_papel_de_trabajo,
)
from auditoria.services.template_file_registry import TemplateFileRegistry
from auditoria.services.work_paper_validator import WorkPaperValidator
from users.models import Roles

Usuario = get_user_model()

VERDE = PatternFill(start_color='FFC6EFCE', end_color='FFC6EFCE', fill_type='solid')

CARPETA = '4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS'
DOCUMENTO = '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'


def _jefe(username):
    """Usuario con rol de jefe (Audit.save lo exige)."""
    rol, _ = Roles.objects.get_or_create(
        name='audit_manager', defaults={'verbose_name': 'Jefe'})
    return Usuario.objects.create_user(
        username=username, email=f'{username}@auditapro.test',
        password='Clave.2026', role=rol, plan='A',
        first_name='Mario', last_name='García')


def _excel_de_marcas(filas):
    """Excel de marcas con las filas en verde (las que el sistema importa)."""
    libro = Workbook()
    hoja = libro.active
    hoja.append(['Símbolo', 'Descripción', 'Papel de Trabajo'])
    for indice, (simbolo, descripcion, papel) in enumerate(filas, start=2):
        hoja.append([simbolo, descripcion, papel])
        for columna in range(1, 4):
            hoja.cell(row=indice, column=columna).fill = VERDE

    memoria = io.BytesIO()
    libro.save(memoria)
    return SimpleUploadedFile(
        'MARCAS.xlsx', memoria.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


class CanonizarPapelDeTrabajo(SimpleTestCase):
    """Los ejemplos exactos de la guía del cliente."""

    def test_ejemplo_de_la_pantalla_2(self):
        self.assertEqual(
            canonizar_papel_de_trabajo('2_CEDULA_SUMARIA_CAJA_BANCOS.XLSX'),
            'CEDULA SUMARIA CAJA BANCOS')

    def test_ejemplo_de_la_pantalla_1(self):
        self.assertEqual(
            canonizar_papel_de_trabajo('2 SUMARIA CAJAS Y BANCOS.xlsx'),
            'SUMARIA CAJAS Y BANCOS')

    def test_minusculas(self):
        self.assertEqual(
            canonizar_papel_de_trabajo('sumaria cajas y bancos'),
            'SUMARIA CAJAS Y BANCOS')

    def test_lo_que_ya_estaba_bien_no_cambia(self):
        self.assertEqual(
            canonizar_papel_de_trabajo('SUMARIA CAJAS Y BANCOS'),
            'SUMARIA CAJAS Y BANCOS')

    def test_numero_con_decimales_y_espacios_de_sobra(self):
        self.assertEqual(
            canonizar_papel_de_trabajo('  4.1   pasivos.xlsx '), 'PASIVOS')

    def test_un_nombre_que_solo_es_numero_no_se_vacia(self):
        self.assertEqual(canonizar_papel_de_trabajo('4.1'), '4.1')

    def test_vacio(self):
        self.assertEqual(canonizar_papel_de_trabajo(''), '')
        self.assertIsNone(canonizar_papel_de_trabajo(None))


class RegistroDePlantillas(TestCase):
    """Revisoría Fiscal faltaba en el registro que valida los nombres."""

    def test_el_registro_incluye_revisoria(self):
        registro = TemplateFileRegistry(use_cache=False)
        nombres = [f.filename for f in registro.get_all_files()]
        self.assertTrue(
            any('CUESTIONARIOS' in n.upper() for n in nombres),
            'las plantillas de Revisoría Fiscal no están en el registro')

    def test_una_marca_de_revisoria_se_reconoce(self):
        TemplateFileRegistry(use_cache=False).refresh_cache()
        resultado = WorkPaperValidator().validate_work_paper_name('CUESTIONARIOS')
        self.assertTrue(resultado.is_valid, resultado.error_message)


class ImportacionSigueLaInstruccion(TestCase):
    """La carga guarda el nombre ya canonizado y separa avisos de advertencias."""

    def setUp(self):
        TemplateFileRegistry(use_cache=False).refresh_cache()
        self.jefe = _jefe('jefe_marcas')
        self.auditoria = Audit.objects.create(
            title='Financiera', identidad='Cliente', tipoAuditoria='F', moneda='GTQ',
            audit_manager=self.jefe, fechaInit='2025-01-01', fechaEnd='2025-12-31')

    def _importar(self, filas):
        servicio = AuditMarkImportService(self.auditoria.id, _excel_de_marcas(filas))
        return servicio, servicio.import_marks(replace_existing=True)

    def test_el_nombre_se_guarda_en_la_forma_de_la_instruccion(self):
        _, resultado = self._importar([
            ('✓', 'Verificado', '2_cedula_sumaria_caja_bancos.xlsx'),
        ])
        self.assertEqual(resultado['marks_imported'], 1)

        marca = self.auditoria.audit_marks.get()
        self.assertEqual(marca.work_paper_number, 'CEDULA SUMARIA CAJA BANCOS')

    def test_la_correccion_se_informa_como_aviso_y_no_como_advertencia(self):
        _, resultado = self._importar([
            ('✓', 'Verificado', 'cedula sumaria caja bancos'),
        ])
        self.assertEqual(resultado['marks_corrected'], 1)
        self.assertEqual(len(resultado['avisos']), 1)
        self.assertIn('CEDULA SUMARIA CAJA BANCOS', resultado['avisos'][0])
        self.assertEqual(resultado['errors'], [],
                         'escribir en minúsculas ya no es una advertencia')

    def test_un_nombre_ya_correcto_no_genera_aviso(self):
        _, resultado = self._importar([
            ('✓', 'Verificado', 'CEDULA SUMARIA CAJA BANCOS'),
        ])
        self.assertEqual(resultado['marks_corrected'], 0)
        self.assertEqual(resultado['avisos'], [])
        self.assertEqual(resultado['errors'], [])

    def test_un_nombre_inexistente_si_advierte_y_sugiere(self):
        _, resultado = self._importar([
            ('✓', 'Verificado', 'CEDULA SUMARIA CAJA BANKOS'),
        ])
        self.assertEqual(len(resultado['errors']), 1)
        self.assertIn('no corresponde a ninguna plantilla', resultado['errors'][0])
        self.assertIn('¿Quiso decir', resultado['errors'][0])
        self.assertEqual(resultado['marks_imported'], 1,
                         'la marca se importa igual, solo se avisa')

    def test_la_sugerencia_viene_en_la_forma_de_la_instruccion(self):
        """No el nombre crudo del archivo ('_CEDULA_SUMARIA_CAJA_BANCOS')."""
        _, resultado = self._importar([
            ('Σ', 'Sumatoria', 'SUMARIA CAJAS Y BANCOS'),
        ])
        self.assertEqual(len(resultado['errors']), 1)
        self.assertIn("¿Quiso decir 'CEDULA SUMARIA CAJA BANCOS'?",
                      resultado['errors'][0])

    def test_una_marca_sin_papel_de_trabajo_no_advierte(self):
        _, resultado = self._importar([('✓', 'Verificado', None)])
        self.assertEqual(resultado['marks_imported'], 1)
        self.assertEqual(resultado['errors'], [])
        self.assertEqual(resultado['avisos'], [])


class LaMarcaEnMinusculasLlegaAlPapel(TestCase):
    """Prueba de punta a punta: cargar en minúsculas y descargar la cédula."""

    def setUp(self):
        TemplateFileRegistry(use_cache=False).refresh_cache()
        self.jefe = _jefe('jefe_e2e')
        self.auditoria = Audit.objects.create(
            title='Financiera', identidad='Cliente', tipoAuditoria='F', moneda='GTQ',
            audit_manager=self.jefe, fechaInit='2025-01-01', fechaEnd='2025-12-31')

    def test_la_marca_cargada_en_minusculas_se_pega_en_la_cedula(self):
        servicio = AuditMarkImportService(
            self.auditoria.id,
            _excel_de_marcas([('✓', 'Verificado', '2_cedula_sumaria_caja_bancos.xlsx')]))
        servicio.import_marks(replace_existing=True)

        cliente = Client()
        cliente.force_login(self.jefe)
        respuesta = cliente.get(
            f'/auditoria/download/{self.auditoria.id}/'
            f'{urllib.parse.quote(CARPETA)}/{urllib.parse.quote(DOCUMENTO)}/')
        self.assertEqual(respuesta.status_code, 200)

        contenido = b''.join(respuesta.streaming_content)
        hoja = load_workbook(io.BytesIO(contenido)).worksheets[0]
        textos = [
            str(hoja.cell(row=fila, column=col).value)
            for fila in range(1, min(hoja.max_row, 120) + 1)
            for col in range(1, min(hoja.max_column, 20) + 1)
            if hoja.cell(row=fila, column=col).value
        ]
        self.assertTrue(any('Verificado' in t for t in textos),
                        'la marca no llegó a la cédula')
