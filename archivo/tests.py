from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .views import DOCUMENTS


User = get_user_model()


class PermanentFileTemplateDownloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="archive-user",
            password="test-password",
            first_name="Archivo",
            last_name="Prueba",
        )
        self.client.force_login(self.user)

    def test_downloads_allowed_production_template(self):
        document = DOCUMENTS[0]

        response = self.client.get(
            reverse(
                "descargar_archivo",
                args=[document["archivo"]],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            document["archivo"],
            response["Content-Disposition"],
        )

    def test_rejects_unknown_template(self):
        response = self.client.get(
            reverse(
                "descargar_archivo",
                args=["documento-no-permitido.docx"],
            )
        )

        self.assertEqual(response.status_code, 404)
