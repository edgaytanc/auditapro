"""Prueba real pedida por el cliente: papel «10_INTEGRACION_EGRESOS» (Financiera · Pruebas sustantivas · Caja y bancos).

Libro de egresos 2025 (70 partidas) + facturas en PDF + contrato de arrendamiento en Word (ver ``fixtures_egresos``).
"""
import unittest
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook

from analisis.models import CorridaAnalisis

from . import fixtures_egresos as fx
from .base import AnalisisCase

PLANTILLA = Path(settings.BASE_DIR) / "static/templates_base_financiera/4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS/10_INTEGRACION_EGRESOS.xlsx"


@unittest.skipUnless(PLANTILLA.is_file(), "plantilla real no presente")
class PruebaDeGastosA12(AnalisisCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.run_ = self.start(
            plantilla=self.upload(PLANTILLA.name, PLANTILLA.read_bytes()),
            auxiliares=[self.upload("Libro_de_egresos_2025.xlsx", fx.libro_xlsx())],
            soportes=[self.upload("Soportes_egresos_2025.pdf", fx.soportes_pdf()),
                      self.upload("Contrato_arrendamiento_Los_Arcos.docx", fx.contrato_docx())],
            instruccion="Prueba de gastos: integra los egresos del año, cruza con facturas y contratos y busca pagos inusuales.",
            parametros={"fecha_cierre": "2025-12-31", "saldo_mayor": str(fx.total_libro()), "limite_autorizacion": "10000"},
        )
        self.assertEqual(self.run_.estado, CorridaAnalisis.Estado.TERMINADO, self.run_.error_mensaje)
        self.version = self.run_.versiones.get(numero=1)
        self.wb = load_workbook(self.version.archivo.path)
        self.ws = self.wb["PT A-12 Egresos"]

    def test_orquestador_reconoce_papel_de_egresos(self):
        self.assertEqual(self.run_.plan["kind_ref"], "G-1")
        activos = {a["agent"] for a in self.run_.plan["agents"] if a["active"]}
        self.assertEqual(activos, {"masivo", "predictivo", "fraudes", "contratos"})

    def test_cada_partida_en_la_tabla_del_papel_y_cuadra_con_el_mayor(self):
        est = self.version.informe["estructura"]
        self.assertEqual((est["modo"], est["filas"], est["insertadas"], est["cuadre"]), ("partidas", 70, 55, "PT A-12 Egresos!H97"))
        ws = self.ws
        total = sum(Decimal(str(ws[f"F{r}"].value)) for r in range(23, 93))
        self.assertEqual(total.quantize(Decimal("0.01")), fx.total_libro())
        self.assertEqual(ws["F93"].value, "=SUM(F23:F92)")  # el total del papel creció con la tabla
        self.assertEqual((ws["H96"].value, ws["H98"].value), ("=F93", "=H96-H97"))
        self.assertEqual(Decimal(str(ws["H97"].value)), fx.total_libro())
        self.assertEqual((ws["A23"].value, ws["A92"].value), (1, 70))
        self.assertIn("Origen", ws["F23"].comment.text)
        self.assertEqual(self.version.informe["formulas_sobrescritas"], 0)

    def test_observaciones_de_cada_partida_en_su_columna(self):
        obs = {}
        for r in range(23, 93):
            desc, o = str(self.ws[f"D{r}"].value or ""), str(self.ws[f"I{r}"].value or "")
            self.assertTrue(o, f"fila {r} sin análisis")
            obs.setdefault(desc.split(" — ")[0], []).append(o)
        flat = {k: " ".join(v) for k, v in obs.items()}
        self.assertIn("Posible duplicado", flat["Distribuidora de Combustibles Petro"])
        self.assertIn("Bajo el límite de autorización", flat["Servicios Varios López"])
        self.assertIn("importe difiere: documento 3,480.00 vs. auxiliar 3,840.00", flat["Taller El Rápido"])
        self.assertIn("Posterior al vencimiento del contrato", flat["Inmobiliaria Los Arcos, S.A."])
        self.assertIn("Proveedor ocasional con pago alto", flat["Fundación Esperanza"])
        self.assertIn("Sin alertas", " ".join(flat.values()))
        self.assertEqual(self.wb.sheetnames, ["PT A-12 Egresos", "ANÁLISIS AGENTES", "Evidencia"])

    def test_pagos_recurrentes_no_son_duplicados(self):
        codes = " ".join(h.resultado for h in self.run_.hallazgos.all())
        self.assertIn("2 partidas repetidas (1 grupo(s)", codes)  # solo Combustibles Petro, no el alquiler ni honorarios
        self.assertFalse(self.run_.hallazgos.filter(resultado__contains="vencidos al cierre").exists())

    def test_hallazgos_de_la_prueba_de_gastos(self):
        res = {h.resultado for h in self.run_.hallazgos.all()}
        self.assertTrue(any("Eventos Premium" in r and "sin registro" in r for r in res))
        self.assertTrue(any("Inmobiliaria Los Arcos" in r and "Q 45,000.00 después del vencimiento" in r for r in res))
        kpis = dict(self.run_.resumen["kpis"])
        self.assertEqual(Decimal(kpis["Monto documental sin cuadrar"]), Decimal("9780.00"))  # 3,480 + 6,300

    def test_conclusion_de_ejemplo_se_sustituye_y_queda_en_comentario(self):
        self.assertTrue(self.ws["A107"].value.startswith("Propuesta de Audita Análisis"))
        self.assertIn("Con base en la revisión de los egresos", self.ws["A107"].comment.text)
        self.assertTrue(self.ws["A102"].value.startswith("• "))
