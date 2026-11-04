"""Casos de aceptación de la guía «4 agentes» §7 con el ejemplo del mockup."""
from decimal import Decimal

from analisis.models import CorridaAnalisis

from . import fixtures
from .base import AnalisisCase


class CruceAcceptance(AnalisisCase):
    def test_cruce_documento_vs_auxiliar(self):
        run = self.sample_run(agentes=["masivo"])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        cruce = self.table(run, "cruce")
        by_doc = {self.text_of(r[0]): (self.text_of(r[3]), self.text_of(r[4])) for r in cruce["rows"]}
        self.assertEqual(by_doc["1099"][0], "Cuadra")
        self.assertEqual(by_doc["1031"][0], "Cuadra")
        self.assertEqual(by_doc["1047"][0], "No cuadra")
        self.assertIn("1,089.00", by_doc["1047"][1])
        self.assertIn("939.00", by_doc["1047"][1])
        self.assertEqual(by_doc["2001"], ("No cuadra", "Documento sin registro en el auxiliar"))

    def test_clasificacion_por_pagina_de_un_pdf_con_varios_documentos(self):
        run = self.sample_run(agentes=["masivo"])
        clasif = self.table(run, "clasificacion")
        tipos = [r[2] for r in clasif["rows"] if r[0] == "Facturas_noviembre.pdf"]
        self.assertEqual(tipos, ["Factura", "Factura", "Factura", "Factura", "Estado de cuenta"])
        word = [r[2] for r in clasif["rows"] if r[0] == "Contrato_Asesorias_Quetzal.docx"]
        self.assertEqual(word, ["Contrato"])

    def test_extraccion_de_campos_con_pagina(self):
        run = self.sample_run(agentes=["masivo"])
        ext = self.table(run, "extraccion")
        fields = {(r[0], r[1], r[3]): self.text_of(r[4]) for r in ext["rows"]}
        self.assertEqual(fields[("Facturas_noviembre.pdf", 1, "Número")], "1099")
        self.assertEqual(fields[("Facturas_noviembre.pdf", 1, "Total")], "41610.00")
        self.assertEqual(fields[("Facturas_noviembre.pdf", 5, "Saldo final")], "125430.10")
        self.assertEqual(fields[("Contrato_Asesorias_Quetzal.docx", 1, "Vence")], "2025-06-30")
        self.assertEqual(fields[("Contrato_Asesorias_Quetzal.docx", 1, "Monto del contrato")], "150000.00")

    def test_kpis_del_resumen(self):
        run = self.sample_run(agentes=["masivo"])
        kpis = dict(run.resumen["kpis"])
        self.assertEqual(kpis["Cuadran"], "2")
        self.assertEqual(kpis["No cuadran"], "2")
        # 1047 (Q 1,089.00) + 2001 (Q 12,480.00)
        self.assertEqual(Decimal(kpis["Monto documental sin cuadrar"]), Decimal("13569.00"))


class ContratosAcceptance(AnalisisCase):
    def test_contratos_clausula_y_facturas_posteriores_al_vencimiento(self):
        run = self.sample_run(agentes=["contratos"], parametros={"fecha_cierre": "2025-12-31"})
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        clauses = self.table(run, "extra:clausulas")
        self.assertTrue(any("Penalización" in self.text_of(r[2]) or "Penalizaci" in self.text_of(r[2]) for r in clauses["rows"]))
        gasto = self.table(run, "extra:gasto")
        row = next(r for r in gasto["rows"] if self.text_of(r[0]) == "Asesorías Quetzal")
        self.assertIn("6 facturas por Q 47,985.00 después del vencimiento", self.text_of(row[4]))

    def test_contrato_leido_de_word_con_monto_y_vencimiento(self):
        run = self.sample_run(agentes=["contratos"], parametros={"fecha_cierre": "2025-12-31"})
        leidos = self.table(run, "extra:contratos")
        row = leidos["rows"][0]
        self.assertEqual(self.text_of(row[2]), "150000.00")
        self.assertEqual(self.text_of(row[3]), "2025-06-30")
        self.assertEqual(self.text_of(row[4]), "Vencido al cierre")

    def test_hallazgo_de_facturas_posteriores_al_vencimiento(self):
        run = self.sample_run(agentes=["contratos"], parametros={"fecha_cierre": "2025-12-31"})
        self.assertTrue(
            run.hallazgos.filter(procedimiento__contains="posteriores al vencimiento", importe=Decimal("47985.00")).exists()
        )


class AgentesAcceptance(AnalisisCase):
    def test_masivo_concentracion_y_total(self):
        run = self.sample_run(agentes=["masivo"], parametros={"fecha_cierre": "2025-12-31"})
        total = sum(Decimal(str(r[3])) for r in fixtures.auxiliar_rows()[1:])
        main = self.table(run, "analisis:masivo")
        total_row = next(r for r in main["rows"] if r[0] == "TOTAL")
        self.assertEqual(Decimal(self.text_of(total_row[2])), total)
        # Asesorías Quetzal concentra más del 30 % por la factura de Q 41,610
        quetzal = next(r for r in main["rows"] if r[0] == "Asesorías Quetzal")
        self.assertEqual(main["flags"][main["rows"].index(quetzal)], "warn")
        self.assertTrue(run.hallazgos.filter(tipo="riesgo", procedimiento__contains="Concentración").exists())

    def test_masivo_cuadra_contra_el_mayor(self):
        # el total del auxiliar de ejemplo es exactamente Q 117,667.00
        run = self.sample_run(agentes=["masivo"], parametros={"saldo_mayor": "117,667.00"})
        cuadre = self.table(run, "extra:cuadre")
        self.assertFalse(cuadre["flagged"])
        self.assertEqual(cuadre["rows"][2][0], "Diferencia: cuadra ✓")
        self.assertFalse(run.hallazgos.filter(procedimiento="Auxiliar vs. mayor").exists())

    def test_masivo_diferencia_contra_el_mayor(self):
        run = self.sample_run(agentes=["masivo"], parametros={"saldo_mayor": "117,000.00"})
        cuadre = self.table(run, "extra:cuadre")
        self.assertTrue(cuadre["flagged"])
        hallazgo = run.hallazgos.get(tipo="hallazgo", procedimiento="Auxiliar vs. mayor")
        self.assertEqual(hallazgo.importe, Decimal("667.00"))
        self.assertEqual(hallazgo.alerta, "Alta")

    def test_masivo_sin_saldo_mayor_marca_integridad_no_comprobada(self):
        run = self.sample_run(agentes=["masivo"])
        self.assertTrue(run.hallazgos.filter(tipo="riesgo", procedimiento__contains="no comprobada").exists())

    def test_predictivo_serie_mensual_y_proyeccion(self):
        run = self.sample_run(agentes=["predictivo"])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        main = self.table(run, "analisis:predictivo")
        labels = [r[0] for r in main["rows"]]
        self.assertEqual(labels[-3:], ["Proyección +1", "Proyección +2", "Proyección +3"])
        self.assertEqual(sum(1 for lbl in labels if str(lbl).startswith("2025-")), 12)
        # noviembre concentra la factura de Q 41,610: sale de la tendencia
        nov = next(r for r in main["rows"] if r[0] == "2025-11")
        self.assertEqual(main["flags"][main["rows"].index(nov)], "warn")

    def test_fraudes_duplicado_atipico_y_benford(self):
        run = self.sample_run(agentes=["fraudes"])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        main = self.table(run, "analisis:fraudes")
        indicadores = {r[0] for r in main["rows"]}
        self.assertIn("Posible duplicado", indicadores)  # factura 1031 repetida en el auxiliar
        self.assertIn("Importe atípico", indicadores)  # la factura de Q 41,610
        benford = next(r for r in main["rows"] if r[0] == "Ley de Benford")
        self.assertIn("referencial", benford[3])  # menos de 300 partidas
        self.assertTrue(run.hallazgos.filter(tipo="hallazgo", procedimiento="Partidas repetidas").exists())
