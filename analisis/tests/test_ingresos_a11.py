"""Regla de pegado del cliente (guía «Prueba de Ingresos PT A-11»), con su plantilla real «9_PRUEBA_DE_INGRESOS».

- Cada factura ocupa una fila de la tabla del papel, en la columna que tiene su nombre; los ejemplos se sustituyen.
- La tabla crece a 500 filas, el total se recalcula y lo de abajo (atributos, control interno, conclusión, firmas) baja.
- En «Observaciones» va el análisis del sistema por transacción.
- Los parámetros de la prueba se completan; lo demás va en las hojas «ANÁLISIS AGENTES» y «Evidencia».
"""
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook

from analisis.models import CorridaAnalisis

from . import fixtures_ingresos as fx
from .base import AnalisisCase

PLANTILLA = Path(settings.BASE_DIR) / "static/templates_base_financiera/4 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS/9_PRUEBA_DE_INGRESOS.xlsx"
HOJA = "PT A-11 PRUEBA INGRESOS"


@unittest.skipUnless(PLANTILLA.is_file(), "plantilla real no presente")
class PruebaDeIngresosA11(AnalisisCase):
    def setUp(self):
        super().setUp()
        self.run_ = self.start(
            plantilla=self.upload(PLANTILLA.name, PLANTILLA.read_bytes()),
            auxiliares=[self.upload("reporte_libro_mayor_auditoria.csv", fx.mayor_csv()),
                        self.upload("reporte_ingresos_auditoria_500.csv", fx.ingresos_csv())],
            soportes=[self.upload("Estado_de_cuenta_octubre_2026.pdf", fx.estado_cuenta_pdf())],
            instruccion="Prueba de ingresos: pega las 500 facturas en el PT A-11 y busca duplicados, atípicos y fines de semana.",
            parametros={"fecha_cierre": "2026-10-31"},
        )
        self.assertEqual(self.run_.estado, CorridaAnalisis.Estado.TERMINADO, self.run_.error_mensaje)
        self.version = self.run_.versiones.get(numero=1)
        self.wb = load_workbook(self.version.archivo.path)
        self.ws = self.wb[HOJA]
        self.rows = fx.facturas()

    def test_usa_el_reporte_de_facturas_y_no_el_mayor(self):
        self.assertEqual(self.run_.plan["kind_ref"], "I-1")
        est = self.version.informe["estructura"]
        self.assertEqual((est["modo"], est["filas"], est["insertadas"]), ("partidas", 500, 490))
        self.assertIn("Monto Doc. (Q) ← Total_Facturado", est["columnas"])
        self.assertIn("Boleta No. ← Referencia_Bancaria", est["columnas"])
        self.assertIn("Banco ← Cuenta_Bancaria_Destino", est["columnas"])

    def test_cada_factura_en_su_columna_y_la_tabla_crece(self):
        ws, first, last = self.ws, self.rows[0], self.rows[-1]
        self.assertEqual([ws[f"{c}19"].value for c in "ABCDGH"], [1, "Factura", first[0], first[0], first[10], first[11]])
        self.assertEqual(ws["E19"].value.strftime("%d/%m/%Y"), first[2])
        self.assertEqual(Decimal(str(ws["F19"].value)), Decimal(first[8]))
        self.assertEqual((ws["A518"].value, ws["C518"].value), (500, last[0]))
        self.assertEqual(ws["F519"].value, "=SUM(F19:F518)")  # el total del papel se agranda solo
        total = sum(Decimal(str(ws[f"F{r}"].value)) for r in range(19, 519)).quantize(Decimal("0.01"))
        self.assertEqual(total, fx.total_facturado())
        # columnas del auditor vacías y la diferencia condicionada a que anote el depósito
        self.assertIsNone(ws["I19"].value)
        self.assertIsNone(ws["J300"].value)
        self.assertIsNone(ws["L19"].value)  # atributos: los ✓ de ejemplo no quedan
        self.assertEqual(ws["K19"].value, '=IF(J19="","",J19-F19)')
        self.assertEqual(ws["K518"].value, '=IF(J518="","",J518-F518)')
        self.assertIn("Total_Facturado", ws["F19"].comment.text + ws["F17"].comment.text)

    def test_lo_de_abajo_baja_con_sus_formulas_y_combinadas(self):
        ws = self.ws
        self.assertTrue(str(ws["A521"].value).startswith("DESCRIPCIÓN DE ATRIBUTOS"))
        self.assertTrue(str(ws["A534"].value).startswith("EVALUACIÓN DEL CONTROL INTERNO"))
        self.assertIn("A519:E519", {str(r) for r in ws.merged_cells.ranges})  # «TOTALES Σ»
        self.assertEqual(ws["A553"].value, "F) ___________________________")  # firmas
        self.assertEqual(self.version.informe["formulas_sobrescritas"], 0)

    def test_observaciones_con_el_analisis_de_cada_transaccion(self):
        ws = self.ws
        obs = [str(ws[f"V{r}"].value or "") for r in range(19, 519)]
        self.assertTrue(all(obs))  # todas las filas tienen su análisis
        self.assertTrue(all(o.startswith(("Cobrado · ", "Pendiente de Cobro · ")) and " — " in o for o in obs))
        dup = [o for o in obs if "Posible duplicado" in o]
        self.assertGreaterEqual(len(dup), 2)
        self.assertTrue(any("Fin de semana" in o or "fin de semana" in o for o in obs))
        self.assertTrue(any("atípic" in o.lower() for o in obs))
        self.assertTrue(any("Sin alertas" in o for o in obs))
        # en ingresos no aplican el límite de autorización (es de pagos) ni la numeración consecutiva de proveedor
        self.assertFalse(any("límite de autorización" in o or "Numeración consecutiva" in o for o in obs))

    def test_correlatividad_de_las_facturas_emitidas(self):
        h = self.run_.hallazgos.get(procedimiento__startswith="Correlatividad")
        self.assertIn("1 número(s) de factura faltantes en 1 salto(s)", h.resultado)
        self.assertIn("202600346 → 202600348", h.condicion)

    def test_parametros_conclusion_y_control_interno(self):
        ws = self.ws
        fechas = sorted(date(int(r[2][6:]), int(r[2][3:5]), int(r[2][:2])) for r in self.rows)
        self.assertEqual(ws["E12"].value, f"{fechas[0]:%d/%m/%Y} al {fechas[-1]:%d/%m/%Y}")
        params = self.version.informe["estructura"]["parametros"]
        self.assertEqual(set(params), {"periodo", "poblacion", "muestra", "metodo", "cuentas"})
        values = {k: ws[v.split("!")[1]].value for k, v in params.items()}
        self.assertEqual((values["poblacion"], values["muestra"]), (500, 500))
        self.assertIn("Cuenta Monetaria Central", values["cuentas"])
        self.assertIn("Cuenta Recaudadora", values["cuentas"])
        self.assertTrue(str(ws["A548"].value).startswith("Propuesta de Audita Análisis"))
        self.assertIn("Con base en las pruebas", ws["A548"].comment.text)  # el texto de ejemplo queda en el comentario
        self.assertEqual([ws[f"T{r}"].value for r in (536, 545)], ["Por evaluar", "Por evaluar"])

    def test_resultados_en_hojas_aparte(self):
        self.assertEqual(self.wb.sheetnames, [HOJA, "ANÁLISIS AGENTES", "Evidencia"])
        an = self.wb["ANÁLISIS AGENTES"]
        titles = [str(c.value) for c in an["A"] if isinstance(c.value, str) and c.value[:2] in ("A.", "B.", "C.", "D.", "E.", "F.", "G.", "H.")]
        self.assertGreaterEqual(len(titles), 3)
        self.assertIsNone(self.ws["A560"].value)  # nada se pega debajo del papel
