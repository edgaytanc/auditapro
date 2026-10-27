"""Regresiones puntuales de años y referencias (no modifica los tests previos)."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase
from django.template.loader import get_template
from auditoria.views import parametros_views
from auditoria.views.utils import generar_html_estructura
from auditoria.urls import urlpatterns


class IntegracionPapelesTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)

    def test_plantilla_conserva_botones_productivos_y_scripts(self):
        template = get_template("auditoria/auditoria-detalle/auditoria_detalle.html")
        source = template.template.source
        actions = (
            "abrirModalGenerarDocumento(", "handleExportCuentas()", "openImportModal()",
            "openAniosModal()", "muestreo_page", "openAuditMarksModal()",
        )
        offsets = [source.index(action) for action in actions]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("_upload-audit-marks-modal.html", source)
        self.assertIn("js/generar_documento_modal.js", source)
        self.assertIn("js/auditoria_detalle.js", source)
        self.assertIn('id="aniosModal"', source)
        self.assertIn("doc_descarga_url", source)
        self.assertIn("audit_marks_upload_url", source)
        self.assertIn("referencia_url", source)
        self.assertIn("Probar Audita Análisis", source)

    def test_circuito_muestra_pasos_y_permite_descarga(self):
        template = get_template("auditoria/auditoria-detalle/_pipeline_papeles.html")
        source = template.template.source
        for marker in (
            'id="apPaperFlow"', 'id="apFlowMarksForm"',
            'id="apFlowFolder"', 'id="apFlowDocument"',
            'id="apFlowDatePrepared"', 'id="apFlowDateApproved"',
            'id="apFlowDownload"', 'download_audit_mark_template',
        ):
            self.assertIn(marker, source)

    def test_rutas_existentes_no_cambian(self):
        names = {item.name for item in urlpatterns}
        self.assertTrue({"anios_auditoria", "referencia_papel", "generar_documento_modal",
                         "importar_cuentas_contables", "muestreo_page"}.issubset(names))

    @patch("auditoria.views.utils.ref_manual", return_value=None)
    @patch("auditoria.views.utils.obtener_ref", return_value="1.2")
    def test_generador_muestra_referencia_editable(self, _obtener, _manual):
        estructura = {"1 DIRECTRICES": {"1 Estatuto.docx": []}}
        generated = generar_html_estructura(estructura, 629, user_verified=True, tipo_auditoria="I")
        self.assertIn("Ref. 1.2", generated)
        self.assertIn('onclick="editarReferencia(this)"', generated)
        self.assertIn('data-archivo="1 Estatuto.docx"', generated)

    @patch.object(parametros_views, "get_audit_for_user_or_404", return_value=SimpleNamespace(tipoAuditoria="I"))
    @patch.object(parametros_views, "obtener_parametros", return_value=SimpleNamespace(anio_actual=2025, anio_anterior=2024, anios_manuales=False))
    @patch.object(parametros_views, "guardar_anios_manuales", return_value=(2026, 2025))
    def test_endpoint_anios_consulta_y_guarda(self, _guardar, _obtener, get_audit):
        request = self.factory.get("/auditoria/detalle/629/anios/")
        request.user = self.user
        response = parametros_views.anios_auditoria(request, 629)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["anio_actual"], 2025)
        request = self.factory.post("/auditoria/detalle/629/anios/",
                                    data=json.dumps({"anio_actual": 2026, "anio_anterior": 2025}),
                                    content_type="application/json")
        request.user = self.user
        response = parametros_views.anios_auditoria(request, 629)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["anio_actual"], 2026)
        self.assertTrue(any(call.kwargs.get("action") == "edit" for call in get_audit.call_args_list))

    @patch.object(parametros_views, "get_audit_for_user_or_404", side_effect=Http404("Acceso denegado"))
    def test_anios_exige_acceso(self, _access):
        request = self.factory.get("/auditoria/detalle/629/anios/")
        request.user = self.user
        with self.assertRaises(Http404):
            parametros_views.anios_auditoria(request, 629)

    @patch.object(parametros_views, "get_audit_for_user_or_404", return_value=SimpleNamespace(tipoAuditoria="I"))
    @patch.object(parametros_views, "ref_automatica", return_value="1.2")
    @patch.object(parametros_views.ReferenciaPapelTrabajo.objects, "update_or_create")
    def test_endpoint_referencia_manual(self, update, _auto, access):
        request = self.factory.post("/auditoria/detalle/629/referencia/",
                                    data=json.dumps({"carpeta": "1 DIRECTRICES", "archivo": "1 Estatuto.docx", "referencia": "1.15"}),
                                    content_type="application/json")
        request.user = self.user
        response = parametros_views.referencia_papel(request, 629)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["referencia"], "1.15")
        self.assertTrue(data["manual"])
        update.assert_called_once()
        self.assertTrue(any(call.kwargs.get("action") == "edit" for call in access.call_args_list))
