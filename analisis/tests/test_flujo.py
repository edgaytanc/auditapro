"""Fase 2: hallazgos de Audita Análisis → plantillas de Hallazgos y Evidencias → revisión → hallazgos finales → informe.

Sigue las «pruebas de aceptación» de las tres guías del cliente (Financiera, Auditoría Interna y Revisoría Fiscal),
con las plantillas reales del sistema.
"""
import re
from datetime import date

from django.urls import reverse
from docx import Document
from openpyxl import load_workbook

from analisis.flujo import config, services as fl
from analisis.models import ArchivoProyecto, BitacoraProyecto, CorridaAnalisis, Hallazgo, HallazgoAnalisis

from . import fixtures_egresos as fx
from .base import AnalisisCase

ALERTAS = ["Alta", "Alta", "Media", "Media", "Baja", "Alta", "Media", "Baja", "Alta", "Media", "Baja", "Alta", "Media", "Baja"]


class FlujoCase(AnalisisCase):
    def setUp(self):
        super().setUp()
        # auditoría de GRUPO: dos auditores asignados (con uno solo sería auditoría individual)
        self.auditor2 = self._user("auditor2", self.role_auditor)
        self.audit.assigned_users.add(self.auditor2)
        self.run_ = self.start(
            auxiliares=[self.upload("Libro_de_egresos_2025.xlsx", fx.libro_xlsx())],
            instruccion="Prueba de gastos del año.", parametros={"limite_autorizacion": "10000"})
        self.assertEqual(self.run_.estado, CorridaAnalisis.Estado.TERMINADO, self.run_.error_mensaje)
        self._extra_hallazgos(14)
        self.ids = list(self.run_.hallazgos.order_by("id").values_list("pk", flat=True))

    def _extra_hallazgos(self, n: int) -> None:
        base = self.run_.hallazgos.count()
        for i in range(base, n):
            HallazgoAnalisis.objects.create(
                corrida=self.run_, orden=i, codigo=f"H-{i + 1:02d}", agente="fraudes", tipo="hallazgo",
                procedimiento=f"Prueba sintética número {i + 1} de pagos", resultado=f"Se encontraron {i + 2} pagos sin soporte",
                importe=1000 * (i + 1), alerta=ALERTAS[i % len(ALERTAS)], nia="NIA 330",
                condicion=f"Condición {i + 1}: pagos sin documento soporte por Q {1000 * (i + 1):,.2f}.",
                criterio="NIA 500: la evidencia debe ser suficiente y apropiada.", causa="Falta de control en el pago.",
                efecto="Riesgo de pagos no autorizados.", recomendacion="Exigir soporte antes de pagar.")

    def archivo(self, clave: str, version: int | None = None) -> ArchivoProyecto:
        q = ArchivoProyecto.objects.filter(audit=self.audit, clave=clave)
        return q.get(version=version) if version else q.order_by("-version").first()

    def libro(self, clave: str, version: int | None = None):
        return load_workbook(self.archivo(clave, version).archivo.path)

    @staticmethod
    def textos_docx(arch) -> list[str]:
        return [p.text for p in Document(arch.archivo.path).paragraphs]


class Financiera(FlujoCase):
    def enviar(self, n=3, cuenta="caja", user=None):
        return fl.enviar_a_papel(user or self.auditor, self.run_, self.ids[:n], destino=cuenta)

    def test_3_hallazgos_de_caja_van_a_h01_h03_con_sus_evidencias(self):
        r = self.enviar(3)
        self.assertEqual(len(r["enviados"]), 3)
        wb = self.libro("hallazgos:caja")
        ws = wb["PT A- HALLAZGOS"]
        self.assertEqual([ws[f"B{i}"].value for i in (11, 12, 13)], ["H-01", "H-02", "H-03"])
        self.assertEqual(ws["C11"].value, "Caja y Bancos")
        self.assertEqual(ws["L11"].value, "Alta")
        self.assertEqual(ws["K11"].value, "En papel de trabajo")
        self.assertEqual(ws["N11"].value, config.MARCA_AUDITA)
        self.assertEqual(ws["A1"].value, "Entidad Distribuidora Andina")
        self.assertEqual(ws["Q1"].value, "A-21")
        self.assertIsNone(ws["E14"].value)  # la fila 4 sigue vacía
        ev = self.libro("evidencias:caja")["PT A- EVIDENCIAS"]
        self.assertEqual([ev[f"B{i}"].value for i in (12, 13, 14)], ["EV-01", "EV-02", "EV-03"])
        self.assertEqual([ev[f"C{i}"].value for i in (12, 13, 14)], ["H-01", "H-02", "H-03"])
        self.assertEqual(ev["P1"].value, "A-22")
        self.assertEqual(ev["D12"].value, "Analítica")

    def test_columnas_nuevas_titulo_clasificacion_responsable(self):
        self.enviar(2)
        ws = self.libro("hallazgos:caja")["PT A- HALLAZGOS"]
        hdr = {str(c.value).split("\n")[0]: c.column_letter for c in ws[10] if c.value}
        self.assertIn("TÍTULO", hdr)
        self.assertIn("CLASIFICACIÓN", hdr)
        self.assertIn("RESPONSABLE", hdr)
        self.assertTrue(ws[f"{hdr['TÍTULO']}11"].value)
        self.assertIn(ws[f"{hdr['CLASIFICACIÓN']}11"].value, config.CLASIFICACIONES_FIN)

    def test_2_hallazgos_de_cuentas_por_cobrar_van_a_b17_no_a_caja(self):
        self.enviar(3, "caja")
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[3:5], destino="cxc")
        ws = self.libro("hallazgos:cxc")["PT A- HALLAZGOS"]
        self.assertEqual(ws["C11"].value, "Cuentas por Cobrar")
        self.assertEqual(ws["Q1"].value, "B-17")
        self.assertEqual(self.libro("evidencias:cxc")["PT A- EVIDENCIAS"]["P1"].value, "B-18")
        caja = self.libro("hallazgos:caja")["PT A- HALLAZGOS"]
        self.assertIsNone(caja["E14"].value)
        self.assertEqual(Hallazgo.objects.filter(audit=self.audit, cuenta="caja").count(), 3)

    def test_reenviar_el_mismo_analisis_no_duplica(self):
        self.enviar(3)
        v = self.archivo("hallazgos:caja").version
        r = self.enviar(3)
        self.assertEqual(r["enviados"], [])
        self.assertEqual(len(r["duplicados"]), 3)
        self.assertEqual(self.archivo("hallazgos:caja").version, v)
        self.assertEqual(Hallazgo.objects.filter(audit=self.audit).count(), 3)

    def test_sin_cuenta_no_se_envia(self):
        with self.assertRaises(fl.FlujoError):
            fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="")

    def test_mas_de_10_hallazgos_agrega_filas_y_el_resumen_cuenta_todos(self):
        self.enviar(14)
        ws = self.libro("hallazgos:caja")["PT A- HALLAZGOS"]
        self.assertEqual(ws["B24"].value, "H-14")
        self.assertEqual(ws["B25"].value, None)
        fila = next(r for r in range(25, ws.max_row + 1) if ws.cell(r, 2).value == "Control Interno")
        tot = [c.value for c in ws[fila] if isinstance(c.value, str) and c.value.startswith("=COUNTIF")]
        self.assertTrue(any("$P$11:$P$24" in t for t in tot), tot)  # el resumen cubre las 14 filas
        self.assertEqual(ws.cell(fila - 1, 4).value, "Crítica")  # la columna Crítica agregada al resumen
        ev = self.libro("evidencias:caja")["PT A- EVIDENCIAS"]
        self.assertEqual(ev["B25"].value, "EV-14")

    def test_la_edicion_manual_en_excel_llega_al_consolidado(self):
        self.enviar(3)
        arch = self.archivo("hallazgos:caja")
        wb = load_workbook(arch.archivo.path)
        wb["PT A- HALLAZGOS"]["E11"] = "CONDICIÓN EDITADA POR EL AUDITOR"
        from analisis.flujo import services as s
        s._guardar_xlsx(self.audit, "hallazgos:caja", wb, "caja", self.auditor, "Edición manual", [])
        fl.enviar_a_revision(self.auditor, self.audit, self.ids[:0] or list(Hallazgo.objects.values_list("pk", flat=True)))
        rev = self.libro("revision")["Registro de Hallazgos"]
        self.assertEqual(rev["B5"].value, "CONDICIÓN EDITADA POR EL AUDITOR")
        self.assertEqual(Hallazgo.objects.get(ref_local="H-01").condicion, "CONDICIÓN EDITADA POR EL AUDITOR")

    def _hasta_revision(self, n=3):
        self.enviar(n)
        pks = list(Hallazgo.objects.filter(audit=self.audit).values_list("pk", flat=True))
        fl.enviar_a_revision(self.auditor, self.audit, pks)
        return [Hallazgo.objects.get(pk=p) for p in pks]

    def test_el_jefe_devuelve_con_comentario_y_no_pasa_a_finales(self):
        h1, h2, h3 = self._hasta_revision()
        with self.assertRaises(fl.FlujoError):
            fl.decidir(self.manager, h1, "devolver", "")
        fl.decidir(self.manager, h1, "devolver", "Falta soporte de la factura")
        h1.refresh_from_db()
        self.assertEqual(h1.estado, config.DEVUELTO)
        ws = self.libro("hallazgos:caja")["PT A- HALLAZGOS"]
        self.assertEqual(ws["K11"].value, "Devuelto")
        fl.decidir(self.manager, h2, "aprobar")
        fl.aprobar_finales(self.manager, self.audit)
        fin = self.libro("finales")["Registro Hallazgos Finales"]
        self.assertEqual(fin["A5"].value, "HF-01")
        self.assertIsNone(fin["A6"].value)

    def test_un_auditor_no_aprueba_y_nadie_aprueba_lo_suyo_en_equipo(self):
        h1, *_ = self._hasta_revision(1)
        with self.assertRaises(fl.FlujoError):
            fl.decidir(self.auditor, h1, "aprobar")
        # el jefe creó el hallazgo: en una auditoría con equipo tampoco aprueba el suyo
        fl.enviar_a_papel(self.manager, self.run_, self.ids[5:6], destino="caja")
        h = Hallazgo.objects.get(creado_por=self.manager)
        fl.enviar_a_revision(self.manager, self.audit, [h.pk])
        with self.assertRaisesMessage(fl.FlujoError, "nadie aprueba sus propios hallazgos"):
            fl.decidir(self.manager, h, "aprobar")

    def test_aprobar_finales_ordena_por_severidad_y_genera_el_informe(self):
        hs = self._hasta_revision(6)
        for h in hs:
            fl.decidir(self.manager, h, "aprobar")
        r = fl.aprobar_finales(self.manager, self.audit)
        fin = self.libro("finales")["Registro Hallazgos Finales"]
        sev = [fin[f"H{i}"].value for i in range(5, 11)]
        self.assertEqual([fin[f"A{i}"].value for i in range(5, 11)], [f"HF-0{i}" for i in range(1, 7)])
        orden = {"Alto": 0, "Medio": 1, "Bajo": 2}
        self.assertEqual(sev, sorted(sev, key=orden.get))
        inf = self.textos_docx(r["informe"])
        self.assertTrue(any(t.startswith("HALLAZGO No. 1:") for t in inf))
        self.assertTrue(any(t.startswith("HALLAZGO No. 6:") for t in inf))
        self.assertTrue(any("CONDICIÓN (Lo que encontramos)" in t for t in inf))
        self.assertTrue(any("Pendiente de respuesta" in t for t in inf))
        self.assertFalse(any("FACTURAS NO AUTORIZADAS POR LA ADMINISTRACIÓN TRIBUTARIA" in t for t in inf))  # el ejemplo se reemplaza
        # el resto del documento queda intacto
        self.assertTrue(any(t.startswith("6. SEGUIMIENTO A RECOMENDACIONES") for t in inf))
        self.assertTrue(any(t.startswith("1. CARTA DE PRESENTACIÓN") for t in inf))
        d = Document(r["informe"].archivo.path)
        self.assertEqual(len(d.tables), 14 + 1)  # la tabla resumen es real
        h = Hallazgo.objects.get(pk=hs[0].pk)
        self.assertEqual(h.estado, config.INCLUIDO)

    def test_reabrir_y_regenerar_crea_v2_y_conserva_v1(self):
        hs = self._hasta_revision(3)
        for h in hs:
            fl.decidir(self.manager, h, "aprobar")
        fl.aprobar_finales(self.manager, self.audit)
        v1 = self.archivo("informe:fin", 1)
        h = Hallazgo.objects.get(pk=hs[0].pk)
        with self.assertRaises(fl.FlujoError):
            fl.reabrir(self.auditor, h, "x")
        fl.reabrir(self.manager, h, "Se corrige la condición")
        h.refresh_from_db()
        self.assertEqual((h.estado, h.bloqueado), (config.EN_REVISION, False))
        r = fl.regenerar(self.manager, self.audit)
        self.assertEqual(r.version, 2)
        self.assertEqual(self.archivo("informe:fin", 1).sha256, v1.sha256)
        n1 = sum(1 for t in self.textos_docx(v1) if t.startswith("HALLAZGO No."))
        n2 = sum(1 for t in self.textos_docx(r) if t.startswith("HALLAZGO No."))
        self.assertEqual((n1, n2), (3, 2))

    def test_el_original_de_la_plantilla_no_se_modifica(self):
        import hashlib
        from pathlib import Path
        base = fl.ruta_base(self.audit, "hallazgos:caja", "caja")
        antes = hashlib.sha256(Path(base).read_bytes()).hexdigest()
        self.enviar(3)
        self.assertEqual(hashlib.sha256(Path(base).read_bytes()).hexdigest(), antes)

    def test_la_bitacora_registra_cada_accion_y_su_cadena_es_valida(self):
        hs = self._hasta_revision(2)
        fl.decidir(self.manager, hs[0], "aprobar")
        acciones = list(BitacoraProyecto.objects.filter(audit=self.audit).values_list("accion", flat=True))
        for a in ("enviar_a_papel", "enviar_a_revision", "decision_aprobar"):
            self.assertIn(a, acciones)
        self.assertTrue(BitacoraProyecto.cadena_valida(self.audit))

    def test_auditoria_individual_el_mismo_usuario_envia_y_aprueba(self):
        self.audit.assigned_users.clear()
        self.assertTrue(fl.es_individual(self.audit))
        self.assertTrue(fl.es_individual(self.audit))
        fl.enviar_a_papel(self.manager, self.run_, self.ids[:2], destino="caja")
        pks = list(Hallazgo.objects.values_list("pk", flat=True))
        fl.enviar_a_revision(self.manager, self.audit, pks)
        for p in pks:
            fl.decidir(self.manager, Hallazgo.objects.get(pk=p), "aprobar")
        self.assertTrue(BitacoraProyecto.objects.filter(audit=self.audit, accion="auditoria_individual").exists())
        r = fl.aprobar_finales(self.manager, self.audit)
        self.assertEqual(r["hallazgos"], 2)

    def test_no_se_aprueba_sin_evidencia(self):
        hs = self._hasta_revision(1)
        hs[0].evidencias.all().delete()
        with self.assertRaisesMessage(fl.FlujoError, "sin evidencia"):
            fl.decidir(self.manager, hs[0], "aprobar")

    def test_sin_hallazgos_aprobados_el_informe_dice_que_no_hay(self):
        r = fl.aprobar_finales(self.manager, self.audit)
        self.assertTrue(any("No se identificaron hallazgos" in t for t in self.textos_docx(r["informe"])))


class AuditoriaInterna(FlujoCase):
    def setUp(self):
        super().setUp()
        self.audit.tipoAuditoria = "I"
        self.audit.save()

    def test_el_area_es_obligatoria(self):
        with self.assertRaisesMessage(fl.FlujoError, "área"):
            fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="")

    def test_3_hallazgos_de_tesoreria_van_a_5_2_con_area_y_evidencias_en_5_3(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:3], destino="tesoreria")
        ws = self.libro("hallazgos:tesoreria")["PT A- HALLAZGOS"]
        self.assertEqual([ws[f"B{i}"].value for i in (11, 12, 13)], ["H-01", "H-02", "H-03"])
        self.assertEqual(ws["C11"].value, "Tesorería")
        self.assertEqual(ws["A2"].value.strip(), "Auditoría Interna")
        self.assertEqual(ws["Q1"].value, "5.2")
        ev = self.libro("evidencias:tesoreria")["PT A- EVIDENCIAS"]
        self.assertEqual(ev["C12"].value, "H-01")
        self.assertEqual(ev["P1"].value, "5.3")

    def test_12_hallazgos_agregan_filas(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:12], destino="compras")
        ws = self.libro("hallazgos:compras")["PT A- HALLAZGOS"]
        self.assertEqual(ws["B22"].value, "H-12")
        self.assertEqual(ws["C22"].value, "Compras")
        fila = next(r for r in range(25, ws.max_row + 1) if ws.cell(r, 2).value == "Control Interno")
        self.assertTrue(any("$P$11:$P$22" in str(c.value) for c in ws[fila]))

    def test_borrador_aprobacion_e_informe_del_area_con_critico_1_y_plazo(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:5], destino="tesoreria", plazo_dias=15,
                          overrides={self.ids[0]: {"severidad": "Crítica"}})
        pks = list(Hallazgo.objects.filter(audit=self.audit).values_list("pk", flat=True))
        fl.enviar_a_revision(self.auditor, self.audit, pks)
        bor = self.libro("borrador")["AI-INF-04-A Comentarios"]
        self.assertEqual(bor["A13"].value, "H-01")
        self.assertIn(bor["C13"].value, ("Crítico", "Alto", "Medio", "Bajo"))
        self.assertIn("Tesorería (5.1.2)", bor["S13"].value)
        self.assertIsNone(bor["F13"].value and None)
        h = Hallazgo.objects.get(ref_local="H-01")
        self.assertEqual(h.severidad, "Crítica")
        fl.decidir(self.manager, h, "aprobar")
        inf = self.textos_docx(self.archivo("informe:tesoreria"))
        self.assertIn("HALLAZGOS CRÍTICOS", inf)
        self.assertTrue(any(t.startswith("CRÍTICO 1:") for t in inf))
        self.assertTrue(any(t.startswith("Plazo: 15 días") for t in inf))
        self.assertTrue(any(t.startswith("Responsable:") for t in inf))
        self.assertTrue(any("VII" in t and "OPINIÓN" in t for t in inf))  # lo demás del informe sigue ahí
        self.assertFalse(any("FALTA CRÍTICA DE SEGREGACIÓN DE FUNCIONES" in t for t in inf))  # el ejemplo se reemplaza

    def test_el_hallazgo_va_solo_al_informe_de_su_area(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="ventas")
        h = Hallazgo.objects.get()
        fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
        fl.decidir(self.manager, h, "aprobar")
        self.assertIsNotNone(self.archivo("informe:ventas"))
        self.assertIsNone(self.archivo("informe:tesoreria"))

    def test_regenerar_crea_version_2(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:2], destino="ventas")
        for h in Hallazgo.objects.all():
            fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
            fl.decidir(self.manager, h, "aprobar")
        v = self.archivo("informe:ventas").version
        r = fl.regenerar(self.manager, self.audit, "ventas")
        self.assertEqual(r.version, v + 1)
        self.assertEqual(sum(1 for t in self.textos_docx(r) if re.match(r"^(CRÍTICO|ALTO|MEDIO|BAJO) \d+:", t)), 2)

    def test_transversal_no_tiene_informe_propio(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="transversal")
        h = Hallazgo.objects.get()
        fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
        fl.decidir(self.manager, h, "aprobar")
        self.assertIsNone(self.archivo("informe:transversal"))


class RevisoriaFiscal(FlujoCase):
    def setUp(self):
        super().setUp()
        self.audit.tipoAuditoria = "R"
        self.audit.save()

    def aprobar(self, n):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:n])
        pks = list(Hallazgo.objects.filter(audit=self.audit).values_list("pk", flat=True))
        fl.enviar_a_revision(self.auditor, self.audit, pks)
        for p in pks:
            fl.decidir(self.manager, Hallazgo.objects.get(pk=p), "aprobar")

    def test_las_plantillas_dicen_revisoria_fiscal(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1])
        ws = self.libro("hallazgos:rf")["PT A- HALLAZGOS"]
        self.assertEqual(ws["A2"].value.strip(), "Revisoría Fiscal")
        self.assertNotIn("INTERNA", str(ws["A4"].value).upper())
        self.assertEqual(ws["Q1"].value, "4.3")
        self.assertIn("quetzales", ws["A5"].value)

    def test_r3_seccion_7_se_reemplaza_sin_tocar_el_resto(self):
        base = load_workbook(fl.ruta_base(self.audit, "comunicacion"))["R-3"]
        otros = {r: base.cell(r, 1).value for r in (11, 12, 16, 21, 26, 31, 36)}
        self.aprobar(3)
        wb = self.libro("comunicacion")
        ws = wb["R-3"]
        enc = next(r for r in range(1, ws.max_row + 1) if str(ws.cell(r, 1).value).startswith("7. HALLAZGOS"))
        self.assertEqual({r: ws.cell(r, 1).value for r in otros}, otros)  # secciones 1 a 6 intactas
        textos = [str(ws.cell(r, 1).value or "") for r in range(enc, ws.max_row + 1)]
        self.assertTrue(textos[1].startswith("Se aprobaron 3 hallazgos"))
        self.assertEqual(sum(1 for t in textos if t.startswith("HALLAZGO ")), 3)
        self.assertTrue(any(t.startswith("Condición:") for t in textos))
        self.assertTrue(any(t.startswith("Evidencias: EV-01") for t in textos))
        self.assertTrue(any(t.startswith("8. CONCEPTO SOBRE LA GESTIÓN") for t in textos))  # la sección 8 solo baja
        self.assertIn(config.NOMBRE_BLOQUE_R3, wb.defined_names)
        amarillo = [c for r in range(enc + 1, enc + 5) for c in [ws.cell(r, 1)] if c.fill.fill_type and c.fill.fgColor.rgb == "FFFFFF00"]
        self.assertEqual(amarillo, [])
        self.assertEqual(wb.sheetnames, load_workbook(fl.ruta_base(self.audit, "comunicacion")).sheetnames)

    def test_regenerar_no_duplica_y_guarda_la_version_2(self):
        self.aprobar(2)
        v = self.archivo("comunicacion").version
        r = fl.regenerar(self.manager, self.audit)
        self.assertEqual(r.version, v + 1)
        ws = load_workbook(r.archivo.path)["R-3"]
        cuenta = sum(1 for row in range(1, ws.max_row + 1) if str(ws.cell(row, 1).value or "").startswith("HALLAZGO "))
        self.assertEqual(cuenta, 2)

    def test_un_hallazgo_devuelto_no_pasa_a_r3(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:2])
        a, b = list(Hallazgo.objects.order_by("id"))
        fl.enviar_a_revision(self.auditor, self.audit, [a.pk, b.pk])
        fl.decidir(self.manager, a, "devolver", "Aclarar el monto")
        fl.decidir(self.manager, b, "aprobar")
        ws = load_workbook(self.archivo("comunicacion").archivo.path)["R-3"]
        cuenta = sum(1 for row in range(1, ws.max_row + 1) if str(ws.cell(row, 1).value or "").startswith("HALLAZGO "))
        self.assertEqual(cuenta, 1)

    def test_el_texto_propio_del_auditor_en_la_seccion_7_se_conserva(self):
        from analisis.flujo import services as s
        wb = load_workbook(fl.ruta_base(self.audit, "comunicacion"))
        ws = wb["R-3"]
        enc = next(r for r in range(1, ws.max_row + 1) if str(ws.cell(r, 1).value).startswith("7. HALLAZGOS"))
        ws.cell(enc + 1, 1).value = "Texto propio del revisor fiscal sobre hallazgos."
        s._guardar_xlsx(self.audit, "comunicacion", wb, "", self.manager, "texto propio", [])
        self.aprobar(1)
        ws = load_workbook(self.archivo("comunicacion").archivo.path)["R-3"]
        todos = [str(ws.cell(r, 1).value or "") for r in range(1, ws.max_row + 1)]
        self.assertIn("Texto propio del revisor fiscal sobre hallazgos.", todos)
        self.assertTrue(any(t.startswith("HALLAZGO 1") for t in todos))


class AuditorIndividual(FlujoCase):
    """Un solo auditor asignado: él mismo envía, revisa, aprueba y genera el informe (sin bloqueo)."""

    def setUp(self):
        super().setUp()
        self.audit.assigned_users.remove(self.auditor2)  # queda solo «auditor1»
        self.assertTrue(fl.es_individual(self.audit))

    def test_el_auditor_unico_hace_todo_el_proceso_financiera(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:3], destino="caja")
        pks = list(Hallazgo.objects.values_list("pk", flat=True))
        fl.enviar_a_revision(self.auditor, self.audit, pks)
        for p in pks:
            fl.decidir(self.auditor, Hallazgo.objects.get(pk=p), "aprobar")  # aprueba lo suyo
        r = fl.aprobar_finales(self.auditor, self.audit)
        self.assertEqual(r["hallazgos"], 3)
        self.assertTrue(BitacoraProyecto.objects.filter(audit=self.audit, accion="auditoria_individual").exists())
        h = Hallazgo.objects.get(pk=pks[0])
        fl.reabrir(self.auditor, h, "Corregir")
        self.assertEqual(fl.regenerar(self.auditor, self.audit).version, 2)

    def test_la_pantalla_le_muestra_los_botones_de_decision(self):
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="caja")
        h = Hallazgo.objects.get()
        fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
        self.client.force_login(self.auditor)
        r = self.client.get(reverse("analisis_hallazgos", args=[self.audit.pk]))
        self.assertContains(r, "Aprobar")
        self.assertContains(r, "Auditoría individual")
        r = self.client.post(reverse("analisis_decidir_hallazgo", args=[self.audit.pk, h.pk]), {"decision": "aprobar"}, follow=True)
        self.assertContains(r, "decisión registrada")
        r = self.client.post(reverse("analisis_generar_informe", args=[self.audit.pk]), follow=True)
        self.assertContains(r, "hallazgo(s) finales")

    def test_interna_y_revisoria_tambien(self):
        for tipo, destino in (("I", "ventas"), ("R", "")):
            Hallazgo.objects.all().delete()
            self.audit.tipoAuditoria = tipo
            self.audit.save()
            fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino=destino)
            h = Hallazgo.objects.get()
            fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
            fl.decidir(self.auditor, h, "aprobar")
            h.refresh_from_db()
            self.assertEqual(h.estado, config.INCLUIDO)

    def test_en_grupo_el_auditor_sigue_sin_poder_aprobar(self):
        self.audit.assigned_users.add(self.auditor2)
        self.assertFalse(fl.es_individual(self.audit))
        fl.enviar_a_papel(self.auditor, self.run_, self.ids[:1], destino="caja")
        h = Hallazgo.objects.get()
        fl.enviar_a_revision(self.auditor, self.audit, [h.pk])
        with self.assertRaises(fl.FlujoError):
            fl.decidir(self.auditor, h, "aprobar")
        with self.assertRaises(fl.FlujoError):
            fl.decidir(self.auditor2, h, "aprobar")
        fl.decidir(self.manager, h, "aprobar")
