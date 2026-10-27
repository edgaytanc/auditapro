from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import Roles
from .enlaces import ENLACES


class PantallasPlanesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        role, _ = Roles.objects.get_or_create(
            name="auditor", defaults={"verbose_name": "Auditor"}
        )
        cls.usuario = get_user_model().objects.create_user(
            username="prueba_planes", password="temporal-prueba", role=role
        )

    def test_paginas_requieren_inicio_de_sesion(self):
        for name in ("planes:mejorar", "planes:renovacion"):
            with self.subTest(ruta=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 302)
                self.assertIn("login", response.url)

    def test_catalogo_y_renovacion_cargan(self):
        self.client.force_login(self.usuario)
        catalogo = self.client.get(reverse("planes:mejorar"))
        self.assertEqual(catalogo.status_code, 200)
        self.assertContains(catalogo, "Individual")
        self.assertContains(catalogo, "Grupos")
        self.assertContains(catalogo, "AUDITAPRO MENSUAL")
        self.assertContains(catalogo, "planes/mejorar.js")

        renovacion = self.client.get(reverse("planes:renovacion"))
        self.assertEqual(renovacion.status_code, 200)
        self.assertContains(renovacion, "Renovar ahora")
        self.assertNotContains(renovacion, "TU PLAN EXPIRA PRONTO")

    def test_cada_checkout_redirige_al_enlace_asignado(self):
        self.client.force_login(self.usuario)
        for slug, enlace in ENLACES.items():
            with self.subTest(plan=slug):
                response = self.client.get(reverse("planes:comprar", args=[slug]))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, enlace)

    def test_checkout_desconocido_da_404(self):
        self.client.force_login(self.usuario)
        response = self.client.get(reverse("planes:comprar", args=["desconocido"]))
        self.assertEqual(response.status_code, 404)
