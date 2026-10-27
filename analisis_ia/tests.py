from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .claude_service import ErrorProveedorIA, ErrorEntradaIA, preparar_adjuntos
from .models import CupoConsultasIA
from .quota import recargar_cinco


class ConsultaIAIntegrationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.usuario = User.objects.create_user(username="auditor@test.com", email="auditor@test.com", password="test-pass-abc")
        self.cliente = Client()
        self.cliente.force_login(self.usuario)
        self.url = reverse("audita_analisis_consultar")

    @patch("analisis_ia.views.verificar_configuracion")
    @patch("analisis_ia.views.consultar_claude", return_value="Orientación de prueba")
    def test_cinco_consultas_y_bloqueo(self, claude, _config):
        for numero in range(5):
            respuesta = self.cliente.post(self.url, {"pregunta": f"Consulta {numero}"})
            self.assertEqual(respuesta.status_code, 200)
            self.assertEqual(respuesta.json()["restantes"], 4-numero)
        respuesta = self.cliente.post(self.url, {"pregunta": "Consulta extra"})
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(claude.call_count, 5)

    @patch("analisis_ia.views.verificar_configuracion")
    @patch("analisis_ia.views.consultar_claude", side_effect=ErrorProveedorIA("No disponible"))
    def test_fallo_claude_reintegra_cupo(self, *_):
        respuesta = self.cliente.post(self.url, {"pregunta": "Prueba"})
        self.assertEqual(respuesta.status_code, 503)
        self.assertEqual(CupoConsultasIA.objects.get(usuario=self.usuario).restantes, 5)

    @patch("analisis_ia.views.verificar_configuracion")
    @patch("analisis_ia.views.consultar_claude", return_value="Leí el archivo")
    def test_archivo_solo_en_memoria_y_cupo(self, claude, _config):
        archivo = SimpleUploadedFile("memo.txt", b"Contenido de la auditoria", content_type="text/plain")
        respuesta = self.cliente.post(self.url, {"pregunta": "Resume", "archivos": archivo})
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("Contenido de la auditoria", str(claude.call_args))
        self.assertEqual(CupoConsultasIA.objects.get(usuario=self.usuario).restantes, 4)

    def test_sin_sesion_no_consulta(self):
        self.cliente.logout()
        self.assertEqual(self.cliente.post(self.url, {"pregunta":"Hola"}).status_code, 302)

    def test_archivo_no_admitido(self):
        archivo = SimpleUploadedFile("malware.exe", b"MZ---", content_type="application/octet-stream")
        respuesta = self.cliente.post(self.url, {"pregunta": "Hola", "archivos": archivo})
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(CupoConsultasIA.objects.filter(usuario=self.usuario).exists())

    def test_recarga_manual_y_version_de_cupo(self):
        cupo = recargar_cinco(self.usuario)
        self.assertEqual(cupo.restantes, 5)
        self.assertEqual(cupo.version_cupo, 1)
        cupo2 = recargar_cinco(self.usuario)
        self.assertEqual(cupo2.restantes, 5)
        self.assertEqual(cupo2.version_cupo, 2)

    def test_admin_no_disponible_a_auditor(self):
        self.assertEqual(self.cliente.get(reverse("audita_analisis_cupos")).status_code, 403)

    def test_csrf_obligatorio_en_post(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        respuesta = cliente.post(self.url, {"pregunta": "Prueba"})
        self.assertEqual(respuesta.status_code, 403)

    @patch("analisis_ia.views.verificar_configuracion")
    @patch("analisis_ia.views.consultar_claude", return_value="OK")
    def test_cupos_aislados_por_usuario(self, *_):
        self.cliente.post(self.url, {"pregunta": "Primera cuenta"})
        otro = get_user_model().objects.create_user(username="otro@test.com", email="otro@test.com", password="otra-pass-abc")
        cliente2 = Client()
        cliente2.force_login(otro)
        respuesta = cliente2.get(reverse("audita_analisis"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(CupoConsultasIA.objects.get(usuario=otro).restantes, 5)
        self.assertEqual(CupoConsultasIA.objects.get(usuario=self.usuario).restantes, 4)

    def test_recarga_superadmin_en_panel_original(self):
        superadmin = get_user_model().objects.create_superuser(
            username="superadmin@test.com", email="superadmin@test.com", password="super-pass-abc"
        )
        self.cliente.force_login(superadmin)
        vista = reverse("audita_analisis_cupos")
        self.assertEqual(self.cliente.get(vista).status_code, 200)
        self.assertEqual(self.cliente.post(vista, {"usuario_id": self.usuario.pk}).status_code, 302)
        self.assertEqual(CupoConsultasIA.objects.get(usuario=self.usuario).restantes, 5)
