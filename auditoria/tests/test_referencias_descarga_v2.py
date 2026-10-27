"""Regresiones: Ref. editable debe viajar al Word/Excel descargado.

Ejecutar: python manage.py test auditoria.tests.test_referencias_descarga_v2
No necesita modificar registros ni migraciones.
"""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase
from docx import Document
from openpyxl import Workbook, load_workbook

from auditoria.services.referencias import inyectar_ref_propia
from auditoria.views import download_views


class ReferenciasDescargaTests(SimpleTestCase):
    def setUp(self):
        self.audit = SimpleNamespace(id=382, tipoAuditoria='F')
        self.factory = RequestFactory()
        self.usuario = SimpleNamespace(is_authenticated=True)

    def test_descarga_word_interna_reemplaza_referencia_real(self):
        ruta = (Path(settings.BASE_DIR) / 'static' / 'templates_base_interna'
                / '1 DIRECTRICES' / '1 Estatuto.docx')
        if not ruta.is_file():
            self.skipTest('La plantilla original 1 Estatuto.docx no está disponible.')

        doc = Document(str(ruta))
        with (patch.object(download_views, 'modify_document_word', return_value=doc),
              patch.object(download_views, 'AuditMarkProcessor') as marcas,
              patch('auditoria.services.referencias.obtener_ref', return_value='DIR-999') as referencia):
            marcas.return_value.process_word_document.side_effect = lambda d: d
            archivo, _ = download_views._process_word_document(
                str(ruta), self.audit, '1 Estatuto.docx', '1 DIRECTRICES', 'I',
            )

        referencia.assert_called_once_with(
            'I', '1 DIRECTRICES', '1 Estatuto.docx', audit_id=382,
        )
        with ZipFile(BytesIO(archivo.getvalue())) as z:
            xml = z.read('word/document.xml').decode('utf-8')
        self.assertIn('DIR-999', xml)
        self.assertNotIn('DIR-001', xml)
        self.assertEqual(xml.count('DIR-999'), 2)  # Copias Word modernas y heredadas

    def test_descarga_excel_reemplaza_referencia_jerarquica(self):
        workbook = Workbook()
        sh = workbook.active
        sh['B2'], sh['C2'] = 'Ref.', '1.9'

        with (patch.object(download_views, 'modify_document_excel', return_value=workbook),
              patch.object(download_views, 'AuditMarkProcessor') as marcas,
              patch.object(download_views, '_apply_revisoria_dynamic_content', side_effect=lambda w, *_: w),
              patch('auditoria.services.referencias.obtener_ref', return_value='1.22') as referencia):
            marcas.return_value.process_excel_document.side_effect = lambda w: w
            archivo, _ = download_views._process_excel_document(
                'modelo.xlsx', self.audit, 'modelo.xlsx', '1 DIRECTRICES', 'I',
            )

        referencia.assert_called_once_with(
            'I', '1 DIRECTRICES', 'modelo.xlsx', audit_id=382,
        )
        output = load_workbook(BytesIO(archivo.getvalue()))
        self.assertEqual(output.active['C2'].value, '1.22')

    def test_no_reemplaza_numeros_normativos(self):
        workbook = Workbook()
        sh = workbook.active
        sh['B2'], sh['C2'] = 'Ref.', 'NIA-530'
        inyectar_ref_propia(workbook, '1.22')
        self.assertEqual(sh['C2'].value, 'NIA-530')

    def test_descarga_directa_pasa_carpeta_y_tipo_elegido(self):
        request = self.factory.get('/auditoria/download/382/1%20DIRECTRICES/1%20Estatuto.docx/?tipo=I')
        request.user = self.usuario
        with (patch.object(download_views, 'get_audit_for_user_or_404', return_value=self.audit),
              patch.object(download_views, 'allowed_audit_type_codes', return_value=['F', 'I']),
              patch.object(download_views, 'get_template_path', return_value='/tmp/modelo.docx'),
              patch.object(download_views.os.path, 'exists', return_value=True),
              patch.object(download_views, '_build_processed_response', return_value=HttpResponse('OK')) as procesar):
            response = download_views.download_document(
                request, 382, '1 DIRECTRICES', '1 Estatuto.docx',
            )
        self.assertEqual(response.status_code, 200)
        procesar.assert_called_once_with(
            '/tmp/modelo.docx', self.audit, '1 Estatuto.docx', '1 DIRECTRICES', 'I',
        )

    def test_descarga_por_patron_pasa_carpeta_y_tipo_elegido(self):
        request = self.factory.get('/auditoria/download/382/A-1/?tipo=F')
        request.user = self.usuario
        info = {'folder': '5 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS',
                'filename': '2 SUMARIA CAJAS Y BANCOS.xlsx',
                'full_path': '/tmp/modelo.xlsx'}
        with (patch.object(download_views, 'get_audit_for_user_or_404', return_value=self.audit),
              patch.object(download_views, 'allowed_audit_type_codes', return_value=['F', 'I']),
              patch.object(download_views, 'get_file_info_from_pattern', return_value=info),
              patch.object(download_views.os.path, 'exists', return_value=True),
              patch.object(download_views, '_build_processed_response', return_value=HttpResponse('OK')) as procesar):
            response = download_views.download_document_by_pattern(request, 382, 'A-1')
        self.assertEqual(response.status_code, 200)
        procesar.assert_called_once_with(
            '/tmp/modelo.xlsx', self.audit, info['filename'], info['folder'], 'F',
        )
