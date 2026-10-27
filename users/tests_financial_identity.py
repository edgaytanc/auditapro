"""Comprobaciones de nombre manual y cabecera de exportación financiera."""
import json
from io import BytesIO
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from .models import FinancialDashboardIdentity


class FinancialIdentityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.first = User.objects.create_user(
            username="financiero1@example.test", password="Password2026Test!",
            email="financiero1@example.test", first_name="Prueba", last_name="Uno",
        )
        self.second = User.objects.create_user(
            username="financiero2@example.test", password="Password2026Test!",
            email="financiero2@example.test", first_name="Prueba", last_name="Dos",
        )

    def test_persistence_per_user(self):
        self.client.force_login(self.first)
        response = self.client.post(reverse("financial_company_save"), {"company_name": "Empresa de Prueba S.A."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FinancialDashboardIdentity.objects.get(user=self.first).company_name, "Empresa de Prueba S.A.")
        self.client.force_login(self.second)
        self.assertFalse(FinancialDashboardIdentity.objects.filter(user=self.second).exists())

    def test_risk_export_contains_company_and_heatmap(self):
        self.client.force_login(self.first)
        response = self.client.post(
            reverse("exportar_matriz_riesgos"),
            data=json.dumps({"company_name": "Empresa Ejemplo S.A.", "riesgos": [{
                "cuenta": "Bancos", "asercion": "Existencia", "saldo": 100,
                "prob": 2, "impacto": 4, "control": "adecuado", "respuesta": "Verificar",
            }]}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(BytesIO(response.content))
        self.assertEqual(wb["Datos"]["B1"].value, "Empresa Ejemplo S.A.")
        self.assertEqual(wb["Mapa de calor"]["B2"].value, "Empresa Ejemplo S.A.")
        self.assertEqual(wb["Datos"]["A4"].value, "Bancos")

    def test_rejects_blank_name(self):
        self.client.force_login(self.first)
        response = self.client.post(reverse("financial_company_save"), {"company_name": "   "})
        self.assertEqual(response.status_code, 400)
