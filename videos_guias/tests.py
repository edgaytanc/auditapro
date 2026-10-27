from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import Roles

from .catalog import GUIDES, VIDEOS


class VideosGuiasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        role, _ = Roles.objects.get_or_create(
            name="auditor", defaults={"verbose_name": "Auditor"}
        )
        cls.usuario = get_user_model().objects.create_user(
            username="prueba_videos_guias",
            password="temporal-prueba",
            role=role,
        )

    def test_modulo_requiere_inicio_de_sesion(self):
        response = self.client.get(reverse("videos_guias:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_modulo_carga_catalogo(self):
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("videos_guias:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Videos y Guías")
        self.assertContains(response, "Canal oficial: Sistema Audita")
        self.assertContains(response, "Guías descargables")
        for video in VIDEOS:
            self.assertContains(response, video["url"])

    def test_todas_las_guias_existen_y_se_pueden_abrir(self):
        self.client.force_login(self.usuario)
        for guide in GUIDES:
            with self.subTest(guide=guide["slug"]):
                expected_path = Path(__file__).resolve().parent / "guides" / guide["filename"]
                self.assertTrue(expected_path.is_file())
                response = self.client.get(reverse("videos_guias:guia", args=[guide["slug"]]))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], "application/pdf")

    def test_guia_desconocida_da_404(self):
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("videos_guias:guia", args=["no-existe"]))
        self.assertEqual(response.status_code, 404)
