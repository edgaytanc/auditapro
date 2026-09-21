"""
Revisión del cliente (7 de agosto de 2026):

    «El botón de muestreo no aparece en Revisoría, solo aparece en Interna y
     Financiera. Este botón de Muestreo debe estar SIEMPRE presente en todos
     los módulos: Financiera, Interna y Revisoría.»

La plantilla de Papeles de Trabajo lo escondía con
`{% if audit.tipoAuditoria != 'R' %}`. El módulo en sí nunca estuvo limitado
—ni las vistas ni los servicios miran el tipo de auditoría—, así que basta con
quitar la condición; estas pruebas fijan que el botón esté en los tres módulos
y que la página del cliente funcione igual en los tres.
"""
import io
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from audits.models import Audit
from users.models import Roles

Usuario = get_user_model()

MODULOS = ('F', 'I', 'R')
PESTANAS = ('Monetario (MUM)', 'Por Atributos', 'Por Criterio')


def _excel_detalle():
    """Detalle transaccional con el formato modelo del cliente."""
    from django.core.files.uploadedfile import SimpleUploadedFile

    libro = Workbook()
    hoja = libro.active
    hoja.append(['N. Documento', 'Descripción', 'Fecha', 'Monto'])
    for numero in range(1, 41):
        hoja.append([f'FAC-{numero:04d}', f'Partida {numero}',
                     '01/03/2025', 1000 * numero])
    memoria = io.BytesIO()
    libro.save(memoria)
    return SimpleUploadedFile('detalle.xlsx', memoria.getvalue())


class MuestreoEnLosTresModulos(TestCase):

    @classmethod
    def setUpTestData(cls):
        rol, _ = Roles.objects.get_or_create(
            name='audit_manager', defaults={'verbose_name': 'Jefe'})
        cls.jefe = Usuario.objects.create_user(
            username='jefe_muestreo', email='jefe_muestreo@auditapro.test',
            password='Clave.2026', role=rol, plan='A',
            first_name='Mario', last_name='García')

    def setUp(self):
        self.cliente = Client()
        self.cliente.force_login(self.jefe)

    def _auditoria(self, tipo):
        return Audit.objects.create(
            title='Auditoría', identidad='Walmart', tipoAuditoria=tipo,
            moneda='GTQ', audit_manager=self.jefe,
            fechaInit='2025-01-01', fechaEnd='2025-12-31')

    def test_el_boton_aparece_en_los_tres_modulos(self):
        for tipo in MODULOS:
            with self.subTest(modulo=tipo):
                auditoria = self._auditoria(tipo)
                respuesta = self.cliente.get(
                    reverse('auditoria_detalle', args=[auditoria.id]))
                html = respuesta.content.decode('utf-8', 'replace')

                self.assertEqual(respuesta.status_code, 200)
                self.assertIn('Muestreo NIA 530', html,
                              f'falta el botón en el módulo {tipo}')
                self.assertIn(reverse('muestreo_page', args=[auditoria.id]), html)

    def test_la_pagina_del_muestreo_abre_en_los_tres_modulos(self):
        for tipo in MODULOS:
            with self.subTest(modulo=tipo):
                auditoria = self._auditoria(tipo)
                respuesta = self.cliente.get(
                    reverse('muestreo_page', args=[auditoria.id]))
                html = respuesta.content.decode('utf-8', 'replace')

                self.assertEqual(respuesta.status_code, 200)
                for pestana in PESTANAS:
                    self.assertIn(pestana, html,
                                  f'falta «{pestana}» en el módulo {tipo}')
                # El encabezado muestra la auditoría real, no el ejemplo
                self.assertIn('Walmart', html)

    def test_la_importacion_del_detalle_funciona_en_los_tres_modulos(self):
        parametros = json.dumps({'nivel_confianza': 95, 'valor_libros': 820000,
                                 'error_tolerable': 54949, 'error_esperado': 8000})
        for tipo in MODULOS:
            with self.subTest(modulo=tipo):
                auditoria = self._auditoria(tipo)
                respuesta = self.cliente.post(
                    reverse('muestreo_importar_datos', args=[auditoria.id]),
                    {'archivo_datos': _excel_detalle(), 'metodo': 'mus',
                     'parametros': parametros})

                self.assertEqual(respuesta.status_code, 200,
                                 respuesta.content[:200])
                self.assertTrue(json.loads(respuesta.content)['success'])

    def test_la_muestra_se_descarga_en_excel_en_los_tres_modulos(self):
        parametros = json.dumps({'nivel_confianza': 95, 'valor_libros': 820000,
                                 'error_tolerable': 54949, 'error_esperado': 8000})
        for tipo in MODULOS:
            with self.subTest(modulo=tipo):
                auditoria = self._auditoria(tipo)
                respuesta = self.cliente.get(
                    reverse('muestreo_descargar', args=[auditoria.id]),
                    {'metodo': 'mus', 'formato': 'excel', 'parametros': parametros})

                self.assertEqual(respuesta.status_code, 200)
                contenido = (respuesta.content if hasattr(respuesta, 'content')
                             else b''.join(respuesta.streaming_content))
                libro = load_workbook(io.BytesIO(contenido))
                self.assertIn('Parámetros', libro.sheetnames)
                self.assertIn('Selección', libro.sheetnames)

    def test_el_formato_modelo_se_descarga_en_los_tres_modulos(self):
        for tipo in MODULOS:
            with self.subTest(modulo=tipo):
                auditoria = self._auditoria(tipo)
                respuesta = self.cliente.get(
                    reverse('muestreo_formato_datos', args=[auditoria.id]))
                self.assertEqual(respuesta.status_code, 200)
