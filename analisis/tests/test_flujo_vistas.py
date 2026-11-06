"""Pantallas y Monitoreo Continuo de la fase 2."""
from datetime import date, timedelta
from io import BytesIO

from django.urls import reverse
from docx import Document
from openpyxl import load_workbook

from analisis.flujo import config, monitoreo, services as fl
from analisis.models import BitacoraProyecto, ExcepcionMonitoreo, Hallazgo

from . import fixtures_egresos as fx
from .test_flujo import FlujoCase


class Pantallas(FlujoCase):
    def test_enviar_desde_el_detalle_y_flujo_completo_por_pantalla(self):
        self.client.force_login(self.auditor)
        r = self.client.get(reverse("analisis_detalle", args=[self.run_.pk]))
        self.assertContains(r, "Enviar a papel de trabajo")
        self.assertNotContains(r, "Claude")
        r = self.client.post(reverse("analisis_enviar_hallazgos", args=[self.run_.pk]),
                             {"ids": self.ids[:2], "destino": "caja", f"sev_{self.ids[0]}": "Crítica"}, follow=True)
        self.assertContains(r, "enviados al papel de trabajo")
        self.assertContains(r, "H-01")
        self.assertEqual(Hallazgo.objects.get(ref_local="H-01").severidad, "Crítica")
        # sin cuenta: mensaje claro, nada se envía
        r = self.client.post(reverse("analisis_enviar_hallazgos", args=[self.run_.pk]), {"ids": self.ids[2:3], "destino": ""}, follow=True)
        self.assertContains(r, "Elija la cuenta contable")
        pks = list(Hallazgo.objects.values_list("pk", flat=True))
        self.client.post(reverse("analisis_a_revision", args=[self.audit.pk]), {"ids": pks})
        # el auditor no puede aprobar
        r = self.client.post(reverse("analisis_decidir_hallazgo", args=[self.audit.pk, pks[0]]), {"decision": "aprobar"}, follow=True)
        self.assertContains(r, "Solo el Jefe de Auditoría")
        self.client.force_login(self.manager)
        r = self.client.post(reverse("analisis_decidir_hallazgo", args=[self.audit.pk, pks[0]]), {"decision": "aprobar"}, follow=True)
        self.assertContains(r, "decisión registrada")
        r = self.client.post(reverse("analisis_generar_informe", args=[self.audit.pk]), follow=True)
        self.assertContains(r, "Informe_Auditoria_Financiera") if False else self.assertContains(r, "hallazgo(s) finales")
        arch = fl.ultima(self.audit, "informe:fin")
        d = self.client.get(reverse("analisis_archivo", args=[self.audit.pk, arch.pk]))
        self.assertEqual(d.status_code, 200)
        self.assertIn("wordprocessingml", d["Content-Type"])
        self.assertTrue(Document(BytesIO(b"".join(d.streaming_content))).paragraphs)

    def test_un_usuario_ajeno_no_ve_los_hallazgos(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="caja")
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("analisis_hallazgos", args=[self.audit.pk])).status_code, 404)
        arch = fl.ultima(self.audit, "hallazgos:caja")
        self.assertEqual(self.client.get(reverse("analisis_archivo", args=[self.audit.pk, arch.pk])).status_code, 404)

    def test_la_bandeja_muestra_estados_y_la_cadena_integra(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:2], destino="cxc")
        self.client.force_login(self.manager)
        r = self.client.get(reverse("analisis_hallazgos", args=[self.audit.pk]))
        self.assertContains(r, "Cuentas por Cobrar")
        self.assertContains(r, "cadena íntegra")
        self.assertTrue(BitacoraProyecto.cadena_valida(self.audit))

    def test_la_bitacora_detecta_si_la_alteran(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="caja")
        b = BitacoraProyecto.objects.filter(audit=self.audit).first()
        BitacoraProyecto.objects.filter(pk=b.pk).update(accion="otra_cosa")
        self.assertFalse(BitacoraProyecto.cadena_valida(self.audit))


class MonitoreoContinuo(FlujoCase):
    def setUp(self):
        super().setUp()
        self.audit.tipoAuditoria = "I"
        self.audit.save()
        self.ex = monitoreo.recibir(self.run_)

    def test_las_excepciones_llegan_solas_y_sin_duplicarse(self):
        self.assertGreaterEqual(len(self.ex), 10)
        n = ExcepcionMonitoreo.objects.count()
        self.assertEqual(monitoreo.recibir(self.run_), [])
        self.assertEqual(ExcepcionMonitoreo.objects.count(), n)
        e = self.ex[0]
        self.assertRegex(e.caso, r"^#[A-Z]{3}-\d{4}-\d{5}$")
        self.assertEqual(e.estado, "pendiente")

    def test_un_analisis_nuevo_de_interna_alimenta_el_monitoreo_via_pipeline(self):
        antes = ExcepcionMonitoreo.objects.count()
        run = self.start(auxiliares=[self.upload("Libro_de_egresos_2025.xlsx", fx.libro_xlsx())], instruccion="Prueba de gastos.",
                         parametros={"limite_autorizacion": "10000"}, titulo="Otra corrida")
        self.assertGreater(ExcepcionMonitoreo.objects.filter(corrida=run).count(), 0)
        self.assertGreater(ExcepcionMonitoreo.objects.count(), antes)

    def test_en_financiera_no_hay_monitoreo(self):
        self.audit.tipoAuditoria = "F"
        self.audit.save()
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("analisis_monitoreo", args=[self.audit.pk])).status_code, 404)

    def test_confirmar_asigna_seguimiento_a_7_dias_y_se_amplia_5(self):
        e = self.ex[0]
        monitoreo.confirmar(self.auditor, e)
        e.refresh_from_db()
        self.assertEqual((e.estado, e.fecha_limite), ("confirmado", date.today() + timedelta(days=7)))
        self.assertEqual(e.auditor_seguimiento, self.auditor)
        monitoreo.ampliar_plazo(self.auditor, e)
        e.refresh_from_db()
        self.assertEqual(e.fecha_limite, date.today() + timedelta(days=12))
        with self.assertRaises(monitoreo.MonitoreoError):
            monitoreo.confirmar(self.auditor, e)

    def test_falso_positivo_no_genera_hallazgo_y_descarta_el_origen(self):
        e = self.ex[1]
        monitoreo.descartar(self.auditor, e)
        e.refresh_from_db()
        e.origen.refresh_from_db()
        self.assertEqual((e.estado, e.origen.decision), ("descartado", "descartado"))
        with self.assertRaises(monitoreo.MonitoreoError):
            monitoreo.convertir_en_hallazgo(self.auditor, e, "tesoreria")

    def test_convertir_en_hallazgo_lo_lleva_a_las_plantillas_del_area(self):
        e = self.ex[0]
        with self.assertRaisesMessage(monitoreo.MonitoreoError, "Primero confirme"):
            monitoreo.convertir_en_hallazgo(self.auditor, e, "tesoreria")
        monitoreo.confirmar(self.auditor, e)
        h = monitoreo.convertir_en_hallazgo(self.auditor, e, "tesoreria")
        e.refresh_from_db()
        self.assertEqual((e.estado, e.hallazgo_id), ("hallazgo", h.pk))
        ws = self.libro("hallazgos:tesoreria")["PT A- HALLAZGOS"]
        self.assertEqual(ws["B11"].value, "H-01")
        self.assertEqual(ws["C11"].value, "Tesorería")
        self.assertIsNotNone(ws["M11"].value)  # fecha de seguimiento = el plazo de monitoreo

    def test_panel_con_indicadores_mapa_de_calor_y_tendencia(self):
        monitoreo.confirmar(self.auditor, self.ex[0])
        p = monitoreo.panel(self.audit)
        self.assertEqual(p["total"], len(self.ex))
        self.assertEqual(sum(n for _, n in p["por_proceso"]), p["total"])
        self.assertEqual(sum(c["n"] for fila in p["calor"] for c in fila["celdas"]), p["total"])
        self.assertEqual(len(p["tendencia"]), 8)
        self.assertEqual(p["tendencia"][-1]["n"], p["total"])
        self.assertEqual(p["pendientes"], len(self.ex) - 1)

    def test_pantalla_y_descargas_excel_pdf_word(self):
        self.client.force_login(self.auditor)
        r = self.client.get(reverse("analisis_monitoreo", args=[self.audit.pk]))
        self.assertContains(r, "Monitoreo Continuo")
        self.assertContains(r, "RECEPCIÓN ACTIVA")
        self.assertNotContains(r, "Claude")
        e = self.ex[0]
        r = self.client.get(reverse("analisis_monitoreo", args=[self.audit.pk]) + f"?caso={e.pk}")
        self.assertContains(r, "Confirmar excepción")
        r = self.client.post(reverse("analisis_monitoreo_accion", args=[self.audit.pk, e.pk]), {"accion": "confirmar"}, follow=True)
        self.assertContains(r, "Convertir en Hallazgo")
        self.assertContains(r, "Ampliar plazo 5 días")
        x = self.client.get(reverse("analisis_monitoreo_descarga", args=[self.audit.pk, e.pk, "xlsx"]))
        self.assertEqual(load_workbook(BytesIO(x.content))["Excepción"]["B3"].value, e.caso)
        w = self.client.get(reverse("analisis_monitoreo_descarga", args=[self.audit.pk, e.pk, "docx"]))
        self.assertTrue(any(e.caso in c.text for t in Document(BytesIO(w.content)).tables for row in t.rows for c in row.cells))
        pdf = self.client.get(reverse("analisis_monitoreo_descarga", args=[self.audit.pk, e.pk, "pdf"]))
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        todo = self.client.get(reverse("analisis_monitoreo_excel", args=[self.audit.pk]))
        wb = load_workbook(BytesIO(todo.content))
        self.assertEqual(wb["Excepciones"].max_row, len(self.ex) + 1)
        self.assertIn("Resumen", wb.sheetnames)

    def test_el_acceso_esta_protegido(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(reverse("analisis_monitoreo", args=[self.audit.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("analisis_monitoreo_excel", args=[self.audit.pk])).status_code, 404)
