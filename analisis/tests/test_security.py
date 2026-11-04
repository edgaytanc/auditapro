"""Subida segura de archivos y protección del sistema contra sobrecarga."""
import io
import zipfile
from datetime import timedelta

from django.test import override_settings
from django.utils import timezone

from analisis import jobs, services
from analisis.models import CorridaAnalisis, DocumentoAnalisis
from analisis.validators import UploadRejected

from . import fixtures
from .base import AnalisisCase


class SubidaDeArchivos(AnalisisCase):
    def reject(self, name, content, **kw):
        with self.assertRaises(UploadRejected) as ctx:
            self.start(auxiliares=[self.upload(name, content)], **kw)
        return str(ctx.exception)

    def test_extension_no_permitida(self):
        self.assertIn("Formato no permitido", self.reject("virus.exe", b"MZ\x90\x00"))
        self.assertIn("Formato no permitido", self.reject("macro.xls", b"\xd0\xcf\x11\xe0"))
        self.assertIn("Formato no permitido", self.reject("script.html", b"<script>alert(1)</script>"))

    def test_contenido_que_no_corresponde_a_la_extension(self):
        self.assertIn("no corresponde", self.reject("factura.pdf", b"esto no es un pdf"))
        self.assertIn("no corresponde", self.reject("foto.png", b"GIF89a....."))
        self.assertIn("dañado", self.reject("aux.xlsx", b"no soy un zip"))

    def test_pdf_con_extension_cambiada_a_xlsx(self):
        self.assertIn("dañado", self.reject("aux.xlsx", fixtures.facturas_pdf()))

    def test_zip_que_no_es_office(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("hola.txt", "hola")
        self.assertIn("no corresponde", self.reject("aux.xlsx", buf.getvalue()))

    def test_bomba_zip_se_rechaza(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", "<Types/>")
            zf.writestr("xl/workbook.xml", "<workbook/>")
            zf.writestr("xl/worksheets/sheet1.xml", b"0" * (80 * 1024 * 1024))
        self.assertLess(len(buf.getvalue()), 2 * 1024 * 1024)
        self.assertIn("compresión sospechosa", self.reject("aux.xlsx", buf.getvalue()))

    def test_csv_binario(self):
        self.assertIn("binarios", self.reject("datos.csv", b"a;b\x00c;d"))

    def test_archivo_vacio(self):
        self.assertIn("vacío", self.reject("aux.csv", b""))

    @override_settings(ANALISIS_MAX_FILE_MB=1)
    def test_limite_por_archivo(self):
        self.assertIn("máximo de 1 MB", self.reject("grande.csv", b"a;b\n" + b"1;2\n" * 400_000))

    @override_settings(ANALISIS_MAX_TOTAL_MB=1, ANALISIS_MAX_FILE_MB=5)
    def test_limite_total_por_analisis(self):
        files = [self.upload(f"a{i}.csv", b"a;b\n" + b"1;2\n" * 150_000) for i in range(3)]
        with self.assertRaises(UploadRejected) as ctx:
            self.start(auxiliares=files)
        self.assertIn("suman más del máximo", str(ctx.exception))

    @override_settings(ANALISIS_MAX_FILES=2)
    def test_limite_de_cantidad_de_archivos(self):
        files = [self.upload(f"a{i}.csv", b"a;b\n1;2\n") for i in range(3)]
        with self.assertRaises(UploadRejected):
            self.start(auxiliares=files)

    def test_un_rechazo_no_deja_archivos_ni_corridas_huerfanas(self):
        files = [self.upload("bien.csv", fixtures.auxiliar_csv()), self.upload("mal.exe", b"MZ")]
        before = CorridaAnalisis.objects.count()
        with self.assertRaises(UploadRejected):
            self.start(auxiliares=files)
        self.assertEqual(CorridaAnalisis.objects.count(), before)
        leftovers = [p for p in __import__("pathlib").Path(self.tmp).rglob("*") if p.is_file()]
        self.assertEqual(leftovers, [])

    def test_los_archivos_se_guardan_con_nombre_aleatorio_y_huella(self):
        run = self.start(auxiliares=[self.upload("../../etc/passwd.csv", fixtures.auxiliar_csv())])
        doc = run.documentos.get()
        self.assertEqual(doc.nombre_original, "passwd.csv")  # sin rutas
        self.assertNotIn("passwd", doc.archivo.name)
        self.assertEqual(len(doc.sha256), 64)

    def test_archivo_ilegible_no_detiene_a_los_demas(self):
        # un PDF con cabecera válida pero contenido roto: se informa y el resto se analiza
        run = self.start(
            auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx())],
            soportes=[self.upload("roto.pdf", b"%PDF-1.4\nbasura sin estructura")], agentes=["masivo"],
        )
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        self.assertTrue(any("roto.pdf" in w for w in run.advertencias))
        self.assertEqual(run.documentos.get(nombre_original="roto.pdf").estado_lectura, "error")

    @override_settings(ANALISIS_MAX_ROWS=20)
    def test_auxiliar_enorme_se_lee_hasta_el_limite_y_se_avisa(self):
        run = self.start(auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx())], agentes=["masivo"])
        self.assertTrue(any("primeras 20 filas" in w for w in run.advertencias))
        self.assertEqual(run.documentos.get().filas_leidas, 19)  # 20 filas leídas = encabezado + 19 de datos


class ProteccionDelSistema(AnalisisCase):
    def activa(self, user, minutes_ago=0):
        run = CorridaAnalisis.objects.create(audit=self.audit, creado_por=user, estado=CorridaAnalisis.Estado.EN_COLA)
        CorridaAnalisis.objects.filter(pk=run.pk).update(latido=timezone.now() - timedelta(minutes=minutes_ago))
        return run

    @override_settings(ANALISIS_MAX_QUEUE=2)
    def test_tope_global_de_corridas_activas(self):
        self.activa(self.manager)
        self.assertIsNone(jobs.capacity_error(self.auditor))
        self.activa(self.auditor)
        self.assertIn("muchos análisis", jobs.capacity_error(self.manager))

    @override_settings(ANALISIS_MAX_ACTIVE_PER_USER=1, ANALISIS_MAX_QUEUE=10)
    def test_tope_por_usuario(self):
        self.activa(self.manager)
        self.assertIn("Ya tiene 1 análisis en proceso", jobs.capacity_error(self.manager))
        self.assertIsNone(jobs.capacity_error(self.auditor))

    @override_settings(ANALISIS_STALE_MINUTES=20)
    def test_corrida_colgada_se_marca_con_error(self):
        viva, colgada = self.activa(self.manager, 1), self.activa(self.manager, 45)
        self.assertEqual(jobs.mark_stale(), 1)
        viva.refresh_from_db(), colgada.refresh_from_db()
        self.assertEqual(viva.estado, CorridaAnalisis.Estado.EN_COLA)
        self.assertEqual(colgada.estado, CorridaAnalisis.Estado.ERROR)
        self.assertIn("interrumpió", colgada.error_mensaje)

    def test_detener_una_corrida_activa(self):
        run = self.activa(self.manager)
        run.estado = CorridaAnalisis.Estado.DETENIDO
        run.save()
        from analisis.pipeline import execute_run

        execute_run(run.pk)  # no arranca una corrida detenida
        run.refresh_from_db()
        self.assertEqual(run.estado, CorridaAnalisis.Estado.DETENIDO)

    def test_solo_documentos_sin_auxiliar_termina_con_aviso(self):
        run = self.start(soportes=[self.upload("Facturas.pdf", fixtures.facturas_pdf())])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        self.assertTrue(any("No se subió un auxiliar" in w for w in run.advertencias))
        self.assertEqual(run.hallazgos.count(), 0)

    def test_pdf_escaneado_queda_como_evidencia_con_aviso(self):
        run = self.start(
            auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx())],
            soportes=[self.upload("escaneo.pdf", fixtures.pdf_sin_texto())], agentes=["masivo"],
        )
        self.assertTrue(any("sin texto" in w and "OCR" in w for w in run.advertencias))
        clasif = self.table(run, "clasificacion")
        self.assertTrue(any(r[2] == "Evidencia sin texto" for r in clasif["rows"]))

    def test_nada_que_analizar_da_error_claro(self):
        run = self.start(soportes=[self.upload("escaneo.pdf", fixtures.pdf_sin_texto())])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.ERROR)
        self.assertIn("No hay nada que analizar", run.error_mensaje)
        self.assertEqual(run.hallazgos.count(), 0)


class Orquestador(AnalisisCase):
    def active(self, run):
        return {a["agent"]: a for a in run.plan["agents"]}

    def test_pagos_activa_masivo_y_fraudes_no_predictivo(self):
        run = self.start(
            auxiliares=[self.upload("Revisión de pagos y proveedores.xlsx", fixtures.auxiliar_xlsx())],
            instruccion="Revisa los pagos: duplicados y pagos inusuales",
        )
        plan = self.active(run)
        self.assertTrue(plan["masivo"]["active"])
        self.assertTrue(plan["fraudes"]["active"])
        self.assertFalse(plan["predictivo"]["active"])
        self.assertTrue(plan["predictivo"]["reason"])
        self.assertEqual(run.plan["kind_ref"], "P-1")

    def test_conciliacion_aritmetica_no_activa_predictivo(self):
        run = self.start(auxiliares=[self.upload("Conciliación bancaria.xlsx", fixtures.auxiliar_xlsx())])
        plan = self.active(run)
        self.assertEqual(run.plan["kind_ref"], "A-3")
        self.assertTrue(plan["masivo"]["active"])
        self.assertFalse(plan["predictivo"]["active"])
        self.assertIn("aritmética", plan["predictivo"]["reason"])

    def test_cuentas_por_cobrar_activa_masivo_y_predictivo(self):
        run = self.start(auxiliares=[self.upload("Cuentas por cobrar antigüedad.xlsx", fixtures.auxiliar_xlsx())])
        plan = self.active(run)
        self.assertEqual(run.plan["kind_ref"], "C-2")
        self.assertTrue(plan["masivo"]["active"] and plan["predictivo"]["active"])

    def test_contratos_subidos_activan_revision_de_contratos(self):
        run = self.sample_run(instruccion="Cruza el auxiliar con las facturas")
        self.assertTrue(self.active(run)["contratos"]["active"])
        self.assertIn("contratos", self.active(run)["contratos"]["reason"].lower())

    def test_el_auditor_puede_forzar_los_agentes(self):
        run = self.sample_run(agentes=["fraudes"])
        plan = self.active(run)
        self.assertEqual([a for a, v in plan.items() if v["active"]], ["fraudes"])
        self.assertEqual(plan["fraudes"]["reason"], "Elegido por el auditor")

    def test_agente_sin_los_datos_que_necesita_se_explica(self):
        csv = "Proveedor;Importe\nA;100\nB;200\n".encode()
        run = self.start(auxiliares=[self.upload("aux.csv", csv)], agentes=["predictivo", "masivo"])
        plan = self.active(run)
        self.assertFalse(plan["predictivo"]["active"])
        self.assertIn("fecha", plan["predictivo"]["reason"].lower())
        self.assertTrue(plan["masivo"]["active"])

    def test_el_original_de_cada_archivo_no_cambia_durante_el_analisis(self):
        run = self.sample_run(agentes=["masivo", "fraudes"])
        for d in run.documentos.all():
            import hashlib

            self.assertEqual(hashlib.sha256(open(d.archivo.path, "rb").read()).hexdigest(), d.sha256)
