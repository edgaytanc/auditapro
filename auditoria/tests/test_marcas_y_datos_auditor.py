"""
Guía de Marcas de Auditoría y Datos Auditor/Jefe (revisión del cliente):

  · Al generar el documento con «Datos Auditor y Jefe» debían llegar JUNTOS los
    datos del auditor y las marcas ya cargadas. Se perdían las marcas.
  · El auditor individual salía como «Sin asignar»: sus datos deben tomarse del
    acceso al sistema.
  · Los datos deben pegar en TODAS las plantillas, también en Revisoría Fiscal.
"""
import io
import urllib.parse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from openpyxl import load_workbook

from audits.models import Audit
from auditoria.models import AuditMark
from auditoria.views.audit_views import nombres_auditor_y_jefe
from users.models import Roles

Usuario = get_user_model()

CARPETA = '4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS'
DOCUMENTO = '2_CEDULA_SUMARIA_CAJA_BANCOS.xlsx'

ETIQUETAS = ('elaboro', 'elaboró', 'reviso', 'revisó', 'hecho por', 'revisado por')


def _datos_y_marcas(contenido):
    """(datos del bloque Elaboró/Revisó, marcas encontradas) de la cédula."""
    libro = load_workbook(io.BytesIO(contenido))
    hoja = libro[libro.sheetnames[0]]
    datos, marcas = {}, []
    for fila in range(1, min(hoja.max_row, 80) + 1):
        for col in range(1, min(hoja.max_column, 40) + 1):
            valor = hoja.cell(row=fila, column=col).value
            if not isinstance(valor, str):
                continue
            etiqueta = valor.strip().rstrip(':').strip().lower()
            if etiqueta in ETIQUETAS:
                contiguo = hoja.cell(row=fila, column=col + 1).value
                if contiguo:
                    datos[etiqueta] = contiguo
            if 'Verificado' in valor:
                marcas.append(valor.strip())
    return datos, marcas


class DatosAuditorYMarcasJuntos(TestCase):

    @classmethod
    def setUpTestData(cls):
        rol = Roles.objects.create(name='audit_manager', verbose_name='Jefe')
        cls.jefe = Usuario.objects.create_user(
            username='jefe_marcas', email='jefe_marcas@auditapro.test',
            password='Clave.2026', role=rol, plan='A',
            first_name='Mario', last_name='García')

    def _auditoria(self, tipo='F', con_asignado=False):
        auditoria = Audit.objects.create(
            title='Auditoría', identidad='Walmart', tipoAuditoria=tipo,
            moneda='GTQ', audit_manager=self.jefe,
            fechaInit='2025-01-01', fechaEnd='2025-12-31')
        if con_asignado:
            auditoria.assigned_users.add(self.jefe)
        AuditMark.objects.create(
            audit=auditoria, symbol='✓', description='Verificado',
            work_paper_number='CEDULA SUMARIA CAJA BANCOS', is_active=True)
        return auditoria

    def _generar(self, auditoria, carpeta=CARPETA, documento=DOCUMENTO):
        cliente = Client()
        cliente.force_login(self.jefe)
        url = (f'/auditoria/detalle/{auditoria.id}/descargar-documento/'
               f'?carpeta={urllib.parse.quote(carpeta)}'
               f'&documento={urllib.parse.quote(documento)}'
               f'&fecha_elaboracion=2026-08-01&fecha_aprobacion=2026-08-02')
        respuesta = cliente.get(url)
        self.assertEqual(respuesta.status_code, 200)
        return (respuesta.content if hasattr(respuesta, 'content')
                else b''.join(respuesta.streaming_content))

    def test_el_documento_generado_conserva_las_marcas(self):
        """El bug del cliente: al generar, la marca desaparecía."""
        contenido = self._generar(self._auditoria())
        _datos, marcas = _datos_y_marcas(contenido)
        self.assertTrue(marcas, 'Se perdió la marca al generar el documento')

    def test_datos_y_marcas_llegan_juntos(self):
        contenido = self._generar(self._auditoria(con_asignado=True))
        datos, marcas = _datos_y_marcas(contenido)
        self.assertTrue(datos, 'No llegaron los datos del auditor')
        self.assertTrue(marcas, 'No llegó la marca de auditoría')

    def test_auditor_individual_no_sale_sin_asignar(self):
        """Sin usuarios asignados, el auditor es quien entró al sistema."""
        auditoria = self._auditoria()
        auditor, jefe = nombres_auditor_y_jefe(auditoria, self.jefe)
        self.assertNotEqual(auditor, 'Sin asignar')
        self.assertIn('Mario', auditor)
        self.assertIn('Mario', jefe)

        contenido = self._generar(auditoria)
        datos, _marcas = _datos_y_marcas(contenido)
        self.assertTrue(datos)
        for valor in datos.values():
            self.assertNotIn('Sin asignar', str(valor))

    def test_en_grupo_manda_el_usuario_asignado(self):
        otro = Usuario.objects.create_user(
            username='auditor_grupo', email='auditor_grupo@auditapro.test',
            password='Clave.2026', role=self.jefe.role, plan='A',
            first_name='Ana', last_name='López')
        auditoria = self._auditoria()
        auditoria.assigned_users.add(otro)
        auditor, jefe = nombres_auditor_y_jefe(auditoria, self.jefe)
        self.assertIn('Ana', auditor)
        self.assertIn('Mario', jefe)

    def test_revisoria_fiscal_recibe_datos_y_marcas(self):
        """
        Las plantillas de Revisoría no traen el recuadro Elaboró/Revisó: el
        sistema lo crea para que igual lleguen los datos.
        """
        auditoria = self._auditoria(tipo='R')
        AuditMark.objects.create(
            audit=auditoria, symbol='✓', description='Verificado',
            work_paper_number='CUESTIONARIOS', is_active=True)
        contenido = self._generar(auditoria, carpeta='2 EJECUCION',
                                  documento='1 CUESTIONARIOS.xlsx')
        datos, marcas = _datos_y_marcas(contenido)
        self.assertTrue(datos, 'Revisoría no recibió los datos del auditor')
        self.assertTrue(marcas, 'Revisoría no recibió la marca')

    def test_no_se_escribe_dentro_del_texto_de_un_cuestionario(self):
        """Etiquetas sueltas como 'Auditor' no deben usarse como ancla."""
        from auditoria.views.audit_views import _inyectar_datos_auditor_jefe
        from openpyxl import Workbook

        libro = Workbook()
        hoja = libro.active
        hoja['A1'] = 'Auditor'          # texto de una pregunta, no el recuadro
        hoja['B1'] = '¿Quién revisó?'
        _inyectar_datos_auditor_jefe(libro, 'Mario García', 'Mario García',
                                     '01-08-2026', '02-08-2026')
        self.assertEqual(hoja['B1'].value, '¿Quién revisó?')
