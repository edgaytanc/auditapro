"""Vistas HTTP: acceso por proyecto, descargas, acciones POST y visor de origen."""
import io

from django.test import Client
from django.urls import reverse
from openpyxl import load_workbook

from analisis.models import CorridaAnalisis

from . import fixtures
from .base import AnalisisCase


class VistasDeAnalisis(AnalisisCase):
    def setUp(self):
        super().setUp()
        self.c = Client()
        self.c.force_login(self.manager)
        self.run_ = self.sample_run(plantilla=self.upload("PT.xlsx", fixtures.plantilla_xlsx()), agentes=["masivo", "fraudes"])

    def test_requiere_inicio_de_sesion(self):
        anon = Client()
        for name, args in [("analisis_home", []), ("analisis_nuevo", []), ("analisis_detalle", [self.run_.pk]),
                           ("analisis_descargar", [self.run_.pk]), ("analisis_csv", [self.run_.pk])]:
            r = anon.get(reverse(name, args=args))
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("login", r["Location"])

    def test_listado_y_detalle_se_muestran(self):
        r = self.c.get(reverse("analisis_home"))
        self.assertContains(r, "Prueba")
        r = self.c.get(reverse("analisis_detalle", args=[self.run_.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Plan del orquestador")
        self.assertContains(r, "CRUCE DOCUMENTO")
        self.assertContains(r, "Documento sin registro en el auxiliar")
        self.assertContains(r, "Pendiente de revisión del auditor")
        self.assertContains(r, "Una alerta no demuestra fraude")

    def test_otro_proyecto_no_puede_ver_ni_descargar_ni_actuar(self):
        other = Client()
        other.force_login(self.outsider)
        pk = self.run_.pk
        for name in ("analisis_detalle", "analisis_estado", "analisis_descargar", "analisis_csv"):
            self.assertEqual(other.get(reverse(name, args=[pk])).status_code, 404, name)
        for name in ("analisis_parar", "analisis_validar", "analisis_aprobar", "analisis_pegar"):
            self.assertEqual(other.post(reverse(name, args=[pk])).status_code, 404, name)
        fid = self.run_.cifras.first().fid
        self.assertEqual(other.get(reverse("analisis_cifra", args=[pk, fid])).status_code, 404)
        self.run_.refresh_from_db()
        self.assertEqual(self.run_.revision, CorridaAnalisis.Revision.PROPUESTO)

    def test_un_auditor_asignado_si_accede_pero_no_aprueba(self):
        a = Client()
        a.force_login(self.auditor)
        self.assertEqual(a.get(reverse("analisis_detalle", args=[self.run_.pk])).status_code, 200)
        a.post(reverse("analisis_aprobar", args=[self.run_.pk]))
        self.run_.refresh_from_db()
        self.assertEqual(self.run_.revision, CorridaAnalisis.Revision.PROPUESTO)

    def test_las_acciones_no_se_aceptan_por_get(self):
        for name in ("analisis_parar", "analisis_validar", "analisis_aprobar", "analisis_rechazar", "analisis_pegar"):
            self.assertEqual(self.c.get(reverse(name, args=[self.run_.pk])).status_code, 405, name)

    def test_csrf_se_exige_en_las_acciones(self):
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.manager)
        self.assertEqual(strict.post(reverse("analisis_aprobar", args=[self.run_.pk])).status_code, 403)

    def test_descarga_del_papel_llenado(self):
        r = self.c.get(reverse("analisis_descargar", args=[self.run_.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn("spreadsheetml", r["Content-Type"])
        self.assertIn("PT_llenado.xlsx", r["Content-Disposition"])
        wb = load_workbook(io.BytesIO(b"".join(r.streaming_content)))
        self.assertEqual(wb["Cédula"]["C6"].value, "=B6*2")

    def test_descarga_csv(self):
        r = self.c.get(reverse("analisis_csv", args=[self.run_.pk]))
        self.assertEqual(r["Content-Type"], "text/csv; charset=utf-8")
        self.assertTrue(r.content.startswith(b"\xef\xbb\xbf"))

    def test_estado_json(self):
        data = self.c.get(reverse("analisis_estado", args=[self.run_.pk])).json()
        self.assertEqual((data["estado"], data["progreso"]), ("terminado", 100))

    def test_validar_aprobar_y_bloqueo_posterior(self):
        r = self.c.post(reverse("analisis_validar", args=[self.run_.pk]), follow=True)
        self.assertContains(r, "cifras cuadran con su origen")
        self.c.post(reverse("analisis_aprobar", args=[self.run_.pk]), {"comentario": "OK"})
        self.run_.refresh_from_db()
        self.assertEqual(self.run_.revision, CorridaAnalisis.Revision.APROBADO)
        r = self.c.post(reverse("analisis_pegar", args=[self.run_.pk]), {"conflicto": "siguiente_libre"}, follow=True)
        self.assertContains(r, "ya está aprobado")

    def test_rechazar_sin_motivo_no_cambia_nada(self):
        self.c.post(reverse("analisis_rechazar", args=[self.run_.pk]), {"comentario": ""})
        self.run_.refresh_from_db()
        self.assertEqual(self.run_.revision, CorridaAnalisis.Revision.PROPUESTO)

    def test_decidir_hallazgo(self):
        h = self.run_.hallazgos.first()
        self.c.post(reverse("analisis_decidir", args=[self.run_.pk, h.pk]), {"decision": "descartado", "nota": ""})
        h.refresh_from_db()
        self.assertEqual(h.decision, "pendiente")  # falta el motivo
        self.c.post(reverse("analisis_decidir", args=[self.run_.pk, h.pk]), {"decision": "descartado", "nota": "Falso positivo"})
        h.refresh_from_db()
        self.assertEqual((h.decision, h.decidido_por), ("descartado", self.manager))

    def test_pegar_de_nuevo_crea_version_2_y_ambas_se_descargan(self):
        self.c.post(reverse("analisis_pegar", args=[self.run_.pk]), {"hoja": "Cédula", "celda": "A2", "conflicto": "siguiente_libre", "conclusion": "on"})
        self.assertEqual(self.run_.versiones.count(), 2)
        r = self.c.get(reverse("analisis_descargar_version", args=[self.run_.pk, 1]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get(reverse("analisis_descargar_version", args=[self.run_.pk, 9])).status_code, 404)

    def test_visor_de_origen_excel_pdf_y_pagina_resaltada(self):
        run = self.run_
        excel = run.cifras.filter(documento_nombre__endswith=".xlsx").exclude(filas=[]).first()
        data = self.c.get(reverse("analisis_cifra", args=[run.pk, excel.fid])).json()
        self.assertTrue(data["vecinas"])
        self.assertTrue(any(v["citada"] for v in data["vecinas"]))
        pdf = run.cifras.get(documento_nombre="Facturas_noviembre.pdf", pagina=1)
        data = self.c.get(reverse("analisis_cifra", args=[run.pk, pdf.fid])).json()
        self.assertTrue(data["tiene_imagen"])
        img = self.c.get(reverse("analisis_cifra_pagina", args=[run.pk, pdf.fid]))
        self.assertEqual(img.status_code, 200)
        self.assertTrue(img.content.startswith(b"\x89PNG"))
        from PIL import Image

        pixels = Image.open(io.BytesIO(img.content)).convert("RGB").getdata()
        self.assertTrue(any(r > 200 and g < 60 and b < 60 for r, g, b in pixels), "no se dibujó el rectángulo rojo")
        self.assertEqual(self.c.get(reverse("analisis_cifra_pagina", args=[run.pk, excel.fid])).status_code, 404)

    def test_nuevo_analisis_por_formulario(self):
        r = self.c.get(reverse("analisis_nuevo"))
        self.assertContains(r, "Proyecto de auditoría")
        self.assertNotContains(r, "Auditoría 2025</option>" * 2)
        before = CorridaAnalisis.objects.count()
        r = self.c.post(reverse("analisis_nuevo"), {
            "audit": self.audit.pk, "titulo": "Desde el formulario", "instruccion": "Revisa pagos", "agentes": ["masivo"],
            "fecha_cierre": "31/12/2025", "saldo_mayor": "117,667.00", "umbral_concentracion": "30",
            "auxiliares": self.upload("aux.xlsx", fixtures.auxiliar_xlsx()),
            "soportes": [self.upload("f.pdf", fixtures.facturas_pdf())],
        })
        self.assertEqual(r.status_code, 302, getattr(r, "context", None) and r.context["form"].errors)
        self.assertEqual(CorridaAnalisis.objects.count(), before + 1)
        run = CorridaAnalisis.objects.latest("pk")
        self.assertEqual(run.parametros["fecha_cierre"], "2025-12-31")
        self.assertEqual(run.parametros["saldo_mayor"], "117667.00")
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)

    def test_nuevo_analisis_rechaza_parametros_invalidos_y_proyecto_ajeno(self):
        r = self.c.post(reverse("analisis_nuevo"), {"audit": self.audit.pk, "fecha_cierre": "no es fecha", "rango": "9999"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors.get("fecha_cierre"))
        self.assertTrue(r.context["form"].errors.get("rango"))
        other = Client()
        other.force_login(self.outsider)
        r = other.post(reverse("analisis_nuevo"), {"audit": self.audit.pk, "auxiliares": self.upload("a.xlsx", fixtures.auxiliar_xlsx())})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["form"].errors.get("audit"))  # su proyecto no está entre los que puede usar

    def test_archivo_rechazado_muestra_mensaje_y_no_crea_corrida(self):
        before = CorridaAnalisis.objects.count()
        r = self.c.post(reverse("analisis_nuevo"), {"audit": self.audit.pk, "auxiliares": self.upload("virus.exe", b"MZ")}, follow=True)
        self.assertContains(r, "Formato no permitido")
        self.assertEqual(CorridaAnalisis.objects.count(), before)

    def test_menu_lateral_incluye_audita_analisis(self):
        r = self.c.get(reverse("analisis_home"))
        self.assertContains(r, "Audita Análisis")
        self.assertContains(r, 'href="/analisis/"')
