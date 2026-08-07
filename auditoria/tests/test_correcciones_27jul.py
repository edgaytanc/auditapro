"""
Pruebas de las 3 correcciones a través de las vistas reales (cliente HTTP de
Django): referencias en Word, MUS sin duplicados y Por Criterio con criterios
de monto, incluida la descarga del papel de trabajo.
"""
import io
import json
import os
import zipfile
from collections import Counter

from django.test import Client, TestCase
from django.urls import reverse
from docx import Document
from openpyxl import load_workbook

from audits.models import Audit
from django.contrib.auth import get_user_model
from users.models import Roles

Usuario = get_user_model()

MAYOR = (r'c:\AAA\JJH\Audita\MUESTREO, REFERENCIAS Y EXCEL NUEVO FINANCIERO'
         r'\2 SUSTITUIR PLANTILLAS  MUESTREO\mayor_auxiliar_ficticio_CxC.xlsx')


class CorreccionesCliente27JUL(TestCase):
    """Las tres cosas que el cliente reportó como no funcionando."""

    @classmethod
    def setUpTestData(cls):
        rol = Roles.objects.create(name='audit_manager', verbose_name='Jefe')
        cls.jefe = Usuario.objects.create_user(
            username='jefe_pruebas', email='jefe_pruebas@auditapro.test',
            password='Clave.Pruebas.2026', role=rol, plan='A',
        )
        cls.auditoria_f = Audit.objects.create(
            title='Auditoría Financiera', identidad='ENTIDAD DEMO, S.A.',
            tipoAuditoria='F', moneda='GTQ', audit_manager=cls.jefe,
            fechaInit='2025-01-01', fechaEnd='2025-12-31',
        )
        cls.auditoria_i = Audit.objects.create(
            title='Auditoría Interna', identidad='ENTIDAD DEMO, S.A.',
            tipoAuditoria='I', moneda='GTQ', audit_manager=cls.jefe,
            fechaInit='2025-01-01', fechaEnd='2025-12-31',
        )

    def setUp(self):
        self.cliente = Client()
        self.cliente.force_login(self.jefe)

    @staticmethod
    def _detalle_error(respuesta):
        """Mensaje de fallo legible tanto para JsonResponse como FileResponse."""
        if getattr(respuesta, 'streaming', False):
            return f'respuesta streaming con estado {respuesta.status_code}'
        return respuesta.content[:300]

    # ---------------------------------------------------------------- Word
    def _descargar_word(self, auditoria, carpeta, archivo):
        url = f'/auditoria/download/{auditoria.id}/{carpeta}/{archivo}/'
        respuesta = self.cliente.get(url)
        self.assertEqual(respuesta.status_code, 200,
                         f'No se pudo descargar {archivo}: {respuesta.status_code}')
        return b''.join(respuesta.streaming_content)

    def test_referencia_llega_a_word_interna(self):
        """El recuadro Ref. de las plantillas Word de Interna se rellena."""
        contenido = self._descargar_word(
            self.auditoria_i, '5 INFORME/8 INFORMES ESPECIFICOS POR AREAS',
            '1 Informe Auditoria Contabilidad.docx')
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'ignore')
        # El código de la plantilla ('INF-1') fue sustituido por la referencia
        self.assertNotIn('>INF-1<', xml,
                         'La plantilla sigue mostrando su código propio INF-1')
        self.assertIn('LOGO ENTIDAD', xml, 'Se dañó el recuadro del logo')

    def test_referencia_llega_a_word_financiera(self):
        """El recuadro Ref. de las plantillas Word de Financiera se rellena."""
        contenido = self._descargar_word(
            self.auditoria_f, '2 PLANEACION/1 Reunion Preliminar y Solicitud',
            '2 Solicitud Informacion.docx')
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'ignore')
        self.assertNotIn('PL-1', xml.replace('PL-1 .2', ''),
                         'Quedó el código PL-1.2 de la plantilla')

    def test_referencia_manual_manda_en_word(self):
        """La referencia que fija el auditor gana sobre la automática, en Word."""
        from auditoria.models import ReferenciaPapelTrabajo
        carpeta = '5 INFORME/8 INFORMES ESPECIFICOS POR AREAS'
        archivo = '1 Informe Auditoria Contabilidad.docx'
        ReferenciaPapelTrabajo.objects.create(
            audit=self.auditoria_i, carpeta=carpeta, archivo=archivo,
            referencia='MI-REF-77')
        contenido = self._descargar_word(self.auditoria_i, carpeta, archivo)
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'ignore')
        self.assertIn('MI-REF-77', xml,
                      'La referencia manual del auditor no llegó al Word')

    def test_word_sin_recuadro_recibe_la_referencia(self):
        """Una plantilla sin recuadro igual muestra su Ref. (antes: ninguna)."""
        contenido = self._descargar_word(
            self.auditoria_i, '1 DIRECTRICES', '2 CODIGO_ETICA.docx')
        documento = Document(io.BytesIO(contenido))
        primeros = ' '.join(p.text for p in documento.paragraphs[:3])
        self.assertIn('Ref.', primeros,
                      'La plantilla sin recuadro quedó sin referencia')

    # -------------------------------------------------------------- Muestreo
    def _generar_desde_archivo(self, metodo, parametros):
        url = reverse('muestreo_importar_datos', args=[self.auditoria_f.id])
        with open(MAYOR, 'rb') as archivo:
            respuesta = self.cliente.post(url, {
                'archivo_datos': archivo,
                'metodo': metodo,
                'parametros': json.dumps(parametros),
            })
        self.assertEqual(respuesta.status_code, 200, respuesta.content[:400])
        cuerpo = json.loads(respuesta.content)
        self.assertTrue(cuerpo['success'], cuerpo)
        return cuerpo

    def test_mus_no_duplica_partidas(self):
        """El bug reportado: MUS repetía documentos en la muestra."""
        cuerpo = self._generar_desde_archivo('mus', {
            'nivel_confianza': 95, 'valor_libros': None,
            'error_tolerable': 500000, 'error_esperado': 50000,
        })
        detalle = cuerpo['data']['detalle_partidas']
        documentos = [fila['documento'] for fila in detalle]
        repetidos = {d: c for d, c in Counter(documentos).items() if c > 1}
        self.assertEqual(repetidos, {},
                         f'MUS sigue duplicando partidas: {list(repetidos)[:5]}')
        self.assertIn('Partidas al 100 % (≥ intervalo)', cuerpo['data']['resultados'])

    def test_criterio_aplica_montos(self):
        """Por Criterio: 100 % sobre el monto mayor y exclusión de triviales."""
        cuerpo = self._generar_desde_archivo('criterio', {
            'valor_total': None, 'porcentaje_examinar': 30,
            'monto_mayor': 50000, 'monto_menor': 1000,
        })
        datos = cuerpo['data']
        detalle = datos['detalle_partidas']
        self.assertTrue(detalle, 'Por Criterio no devolvió partidas')
        # Ninguna partida por debajo del umbral de trivialidad
        self.assertGreaterEqual(min(f['monto'] for f in detalle), 1000)
        # Todas las seleccionadas al 100 % superan el monto mayor
        cien = [f for f in detalle if '100' in (f.get('marca') or '')]
        self.assertTrue(cien, 'No hubo partidas al 100 %')
        self.assertGreaterEqual(min(f['monto'] for f in cien), 50000)
        self.assertIn('Valor objetivo a examinar (Q)', datos['resultados'])
        # Sin duplicados
        documentos = [f['documento'] for f in detalle]
        self.assertEqual(len(documentos), len(set(documentos)))

    def test_criterio_pegado_sin_archivo(self):
        """Por Criterio también funciona con el detalle pegado a mano."""
        partidas = [
            {'documento': 'DOC00013', 'descripcion': 'Transacción 13',
             'fecha': '05/03/2024', 'monto': 500000},
            {'documento': 'DOC00012', 'descripcion': 'Transacción 12',
             'fecha': '01/03/2024', 'monto': 100000},
            {'documento': 'DOC00016', 'descripcion': 'Transacción 16',
             'fecha': '14/03/2024', 'monto': 8500},
            {'documento': 'DOC00019', 'descripcion': 'Transacción 19',
             'fecha': '22/03/2024', 'monto': 720},
        ]
        url = reverse('muestreo_calcular', args=[self.auditoria_f.id])
        respuesta = self.cliente.post(url, data=json.dumps({
            'metodo': 'criterio',
            'parametros': {'partidas': partidas, 'porcentaje_examinar': 30,
                           'monto_mayor': 50000, 'monto_menor': 1000},
        }), content_type='application/json')
        self.assertEqual(respuesta.status_code, 200, respuesta.content[:400])
        datos = json.loads(respuesta.content)['data']
        detalle = datos['detalle_partidas']
        documentos = [f['documento'] for f in detalle]
        # DOC00019 (720) es trivial y queda fuera
        self.assertNotIn('DOC00019', documentos)
        self.assertIn('DOC00013', documentos)

    def test_descarga_excel_del_criterio_incluye_partidas(self):
        """La descarga trae la hoja Selección con partidas y su criterio."""
        parametros = {'valor_total': None, 'porcentaje_examinar': 30,
                      'monto_mayor': 50000, 'monto_menor': 1000}
        cuerpo = self._generar_desde_archivo('criterio', parametros)
        aplicados = cuerpo['parametros_aplicados']

        url = reverse('muestreo_descargar', args=[self.auditoria_f.id])
        respuesta = self.cliente.get(url, {
            'metodo': 'criterio',
            'parametros': json.dumps(aplicados),
            'formato': 'excel',
        })
        self.assertEqual(respuesta.status_code, 200, self._detalle_error(respuesta))
        contenido = b''.join(respuesta.streaming_content)
        libro = load_workbook(io.BytesIO(contenido))
        self.assertIn('Selección', libro.sheetnames)
        hoja = libro['Selección']
        encabezados = [hoja.cell(row=2, column=c).value for c in range(1, 8)]
        self.assertIn('Criterio de selección', encabezados)
        # Filas de datos reales (documento en la 2ª columna)
        self.assertTrue(hoja.cell(row=3, column=2).value,
                        'La hoja Selección salió vacía')

    def test_descarga_excel_del_mus_sin_duplicados(self):
        """El Excel descargado del MUS coincide con lo mostrado y no repite."""
        parametros = {'nivel_confianza': 95, 'valor_libros': None,
                      'error_tolerable': 500000, 'error_esperado': 50000}
        cuerpo = self._generar_desde_archivo('mus', parametros)
        aplicados = cuerpo['parametros_aplicados']

        url = reverse('muestreo_descargar', args=[self.auditoria_f.id])
        respuesta = self.cliente.get(url, {
            'metodo': 'mus', 'parametros': json.dumps(aplicados), 'formato': 'excel'})
        self.assertEqual(respuesta.status_code, 200)
        contenido = b''.join(respuesta.streaming_content)
        hoja = load_workbook(io.BytesIO(contenido))['Selección']
        documentos = [hoja.cell(row=f, column=2).value
                      for f in range(3, hoja.max_row + 1)
                      if hoja.cell(row=f, column=2).value]
        repetidos = {d: c for d, c in Counter(documentos).items() if c > 1}
        self.assertEqual(repetidos, {}, f'El Excel del MUS repite: {list(repetidos)[:5]}')
        self.assertEqual(len(documentos), len(cuerpo['data']['detalle_partidas']),
                         'El Excel descargado no coincide con la muestra mostrada')
