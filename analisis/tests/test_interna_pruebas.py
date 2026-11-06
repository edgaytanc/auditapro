"""Auditoría Interna: sus pruebas de proceso usan tablas de muestra SIN fila TOTAL (terminan en una fila vacía y abajo
un bloque «RESULTADO DE LA PRUEBA» con COUNTA/COUNTIF sobre la tabla). La regla de pegado también aplica ahí.

Plantilla real «1_Pruebas_en_Compras» (hoja AI-CA-01-C Cumplimiento) con el libro de 70 egresos de ``fixtures_egresos``.
"""
import unittest
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook

from analisis import services
from analisis.engine.shared import table_from_dict
from analisis.engine.template_fill import PasteOptions, fill_template

from . import fixtures_egresos as fx
from .base import AnalisisCase

PLANTILLA = Path(settings.BASE_DIR) / "static/templates_base_interna/4 PRUEBAS DE PROCESO/1_Pruebas_en_Compras.xlsx"
HOJA = "AI-CA-01-C Cumplimiento"


@unittest.skipUnless(PLANTILLA.is_file(), "plantilla real no presente")
class PruebaDeComprasAuditoriaInterna(AnalisisCase):
    def setUp(self):
        super().setUp()
        run = self.start(auxiliares=[self.upload("Libro_de_egresos_2025.xlsx", fx.libro_xlsx())])
        hidden = ("clasificacion", "extraccion", "integracion", "integracion_mes", "integracion_fuente")
        tables = [table_from_dict(run.tablas["tablas"][k]) for k in run.tablas["orden"] if k not in hidden]
        out = Path(self.tmp) / "compras_llenado.xlsx"
        self.report = fill_template(PLANTILLA, out, tables=tables, conclusion="c", summary_line="s", sources_line="f",
                                    evidence_rows=[], evidence_note="", options=PasteOptions(),
                                    structure=services._structure_data(run, run.tablas))
        self.wb = load_workbook(out)
        self.ws = self.wb[HOJA]
        self.rows = sorted(fx.libro_rows(), key=lambda r: r[0])

    def test_las_70_partidas_en_la_tabla_de_muestra(self):
        est = self.report.structure
        self.assertEqual((est["tabla"].split("!")[0], est["filas"], est["insertadas"]), (HOJA, 70, 60))
        self.assertIn("No. OC ← No. documento", est["columnas"])
        self.assertIn("Proveedor ← Proveedor (beneficiario)", est["columnas"])
        ws = self.ws
        self.assertEqual((ws["A15"].value, ws["A84"].value), (1, 70))
        self.assertEqual(float(ws["D15"].value), float(self.rows[0][6]))
        self.assertEqual(ws["C15"].value, self.rows[0][3])
        self.assertEqual(self.report.formulas_overwritten, 0)

    def test_el_resultado_de_la_prueba_cuenta_toda_la_tabla(self):
        ws = self.ws
        self.assertEqual(ws["A86"].value, "RESULTADO DE LA PRUEBA")
        self.assertEqual(ws["B87"].value, "=COUNTA(A15:A84)")
        self.assertIn("I15:I84", ws["E87"].value)

    def test_atributos_del_auditor_vacios_y_formulas_en_espera(self):
        ws = self.ws
        self.assertEqual([ws[f"{c}15"].value for c in "EFGH"], [None, None, None, None])  # sin «Sí/No» de ejemplo
        self.assertTrue(ws["I15"].value.startswith('=IF(F15="","",IF(AND(F15="Sí"'))  # no dice «No Cumple» sin evaluar
        self.assertEqual(ws["J15"].value, '=IF(I15="","",IF(I15="Cumple","🟢","🔴"))')
        self.assertTrue(ws["I84"].value.startswith('=IF(F84="","",'))

    def test_la_hoja_que_elige_el_auditor_recibe_los_datos(self):
        run = self.start(auxiliares=[self.upload("Libro_de_egresos_2025.xlsx", fx.libro_xlsx())])
        hidden = ("clasificacion", "extraccion", "integracion", "integracion_mes", "integracion_fuente")
        tables = [table_from_dict(run.tablas["tablas"][k]) for k in run.tablas["orden"] if k not in hidden]
        out = Path(self.tmp) / "compras_aprobaciones.xlsx"
        r = fill_template(PLANTILLA, out, tables=tables, conclusion="c", summary_line="s", sources_line="f",
                          evidence_rows=[], evidence_note="", options=PasteOptions(sheet="AI-CA-01-E Aprobaciones"),
                          structure=services._structure_data(run, run.tablas))
        self.assertEqual(r.structure["tabla"].split("!")[0], "AI-CA-01-E Aprobaciones")
        ws = load_workbook(out)["AI-CA-01-E Aprobaciones"]
        self.assertEqual(ws["A84"].value, 70)

    def test_una_frase_con_muestra_no_es_una_etiqueta_de_parametro(self):
        self.assertTrue(str(self.ws["A12"].value).startswith("Muestra: 10"))
        self.assertIsNone(self.ws["B12"].value)
