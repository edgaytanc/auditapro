"""El papel de trabajo se llena en una COPIA, sin tocar el original ni las fórmulas."""
import hashlib
import io
from pathlib import Path

from openpyxl import Workbook, load_workbook

from analisis import services
from analisis.engine.template_fill import PasteOptions
from analisis.models import CifraAnalisis, CorridaAnalisis, DocumentoAnalisis

from . import fixtures
from .base import AnalisisCase


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LlenadoDelPapel(AnalisisCase):
    def run_with_template(self, **kw):
        return self.sample_run(plantilla=self.upload("PT_ejemplo.xlsx", fixtures.plantilla_xlsx()), agentes=["masivo"], **kw)

    def test_llena_una_copia_y_el_original_queda_intacto(self):
        run = self.run_with_template()
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        tpl = run.plantilla
        self.assertEqual(sha(tpl.archivo.path), tpl.sha256)  # el original no cambió ni un byte
        version = run.ultima_version
        self.assertIsNotNone(version)
        self.assertEqual(version.nombre, "PT_ejemplo_llenado.xlsx")
        self.assertNotEqual(version.sha256, tpl.sha256)

    def test_conserva_formulas_celdas_combinadas_y_hojas(self):
        run = self.run_with_template()
        wb = load_workbook(run.ultima_version.archivo.path)
        ws = wb["Cédula"]
        self.assertEqual(ws["C6"].value, "=B6*2")
        self.assertEqual(ws["B6"].value, 100)
        self.assertIn("A1:D1", [str(r) for r in ws.merged_cells.ranges])
        self.assertEqual(wb["Resumen"]["B1"].value, "=SUM(1,2,3)")
        self.assertIn("Evidencia", wb.sheetnames)

    def test_empieza_bajo_el_encabezado_resultado(self):
        run = self.run_with_template()
        self.assertEqual(run.ultima_version.celda_inicio, "A8")
        ws = load_workbook(run.ultima_version.archivo.path)["Cédula"]
        self.assertTrue(str(ws["A8"].value).startswith("A. CRUCE"))
        self.assertEqual(ws["A9"].fill.fgColor.rgb, "FF1D4FBE")  # encabezado azul #1D4FBE

    def test_cada_cifra_lleva_comentario_con_su_origen(self):
        run = self.run_with_template()
        ws = load_workbook(run.ultima_version.archivo.path)["Cédula"]
        comments = [c.comment.text for row in ws.iter_rows() for c in row if c.comment]
        self.assertTrue(comments)
        self.assertTrue(all(t.startswith("C-") and "Origen:" in t for t in comments))
        self.assertTrue(any("Facturas_noviembre.pdf · pág. 1" in t for t in comments))
        placed = run.cifras.exclude(celda="")
        self.assertEqual(placed.count(), len(comments))

    def test_resumen_conclusion_y_fuentes_debajo(self):
        run = self.run_with_template()
        ws = load_workbook(run.ultima_version.archivo.path)["Cédula"]
        texts = [str(c.value) for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
        self.assertTrue(any(t.startswith("Resumen: Documentos") for t in texts))
        self.assertTrue(any(t.startswith("Conclusión preliminar:") for t in texts))
        self.assertTrue(any("Pendiente de revisión del auditor" in t for t in texts))

    def test_destino_de_cada_hallazgo_o_marca_de_revision(self):
        run = self.run_with_template()
        for h in run.hallazgos.all():
            self.assertTrue(h.destino_pt.startswith("Cédula!") or h.marcado_revision, h.codigo)
        self.assertTrue(run.hallazgos.filter(destino_pt__startswith="Cédula!").exists())

    def test_destino_ocupado_usa_la_siguiente_celda_libre(self):
        run = self.run_with_template()
        version = services.paste_to_template(run, PasteOptions(sheet="Cédula", start="A2"), self.manager)
        self.assertEqual(version.numero, 2)
        self.assertTrue(version.informe["movido_desde"].endswith("A2"))
        ws = load_workbook(version.archivo.path)["Cédula"]
        self.assertEqual(ws["A2"].value, "Cliente: Distribuidora Andina, S.A.")  # no se pisó nada

    def test_cancelar_si_el_destino_no_esta_vacio(self):
        run = self.run_with_template()
        with self.assertRaises(services.PasteError):
            services.paste_to_template(run, PasteOptions(sheet="Cédula", start="A2", conflict="cancelar"), self.manager)
        self.assertEqual(run.versiones.count(), 1)

    def test_sobrescribir_nunca_toca_formulas(self):
        run = self.run_with_template()
        version = services.paste_to_template(run, PasteOptions(sheet="Cédula", start="A6", conflict="sobrescribir"), self.manager)
        ws = load_workbook(version.archivo.path)["Cédula"]
        self.assertEqual(ws["C6"].value, "=B6*2")
        self.assertTrue(any("fórmulas" in w for w in version.informe["advertencias"]))

    def test_texto_de_documento_que_empieza_con_igual_no_se_vuelve_formula(self):
        rows = [["Fecha", "Factura", "Proveedor", "Importe"], [fixtures.date(2025, 1, 5), 1, "=HYPERLINK(\"http://x\",\"x\")", 100],
                [fixtures.date(2025, 1, 6), 2, "Proveedor normal", 200]]
        run = self.start(
            plantilla=self.upload("PT.xlsx", fixtures.plantilla_xlsx()),
            auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx(rows))], agentes=["masivo"],
        )
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        ws = load_workbook(run.ultima_version.archivo.path)["Cédula"]
        found = [c for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value.startswith("=HYPERLINK")]
        self.assertTrue(found)
        self.assertTrue(all(c.data_type == "s" for c in found))

    def test_no_se_puede_pegar_si_ya_esta_aprobado(self):
        run = self.run_with_template()
        services.approve_run(run, self.manager)
        with self.assertRaises(services.PasteError):
            services.paste_to_template(run, PasteOptions(), self.manager)

    def test_xlsm_conserva_macros(self):
        # un .xlsm cualquiera con el contenido de un libro válido: se mantiene la extensión
        run = self.start(
            plantilla=self.upload("PT_macro.xlsm", fixtures.plantilla_xlsx()),
            auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx())], agentes=["masivo"],
        )
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        self.assertTrue(run.ultima_version.nombre.endswith(".xlsm"))

    def test_plantilla_que_no_es_excel_se_rechaza(self):
        from analisis.validators import UploadRejected

        with self.assertRaises(UploadRejected):
            self.start(plantilla=self.upload("PT.docx", fixtures.contrato_docx()), auxiliares=[self.upload("aux.xlsx", fixtures.auxiliar_xlsx())])

    def test_plantilla_con_graficos_avisa_del_riesgo(self):
        from analisis.engine.template_fill import inspect_template
        import zipfile, tempfile

        base = fixtures.plantilla_xlsx()
        src = io.BytesIO(base)
        out = io.BytesIO()
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w") as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("xl/charts/chart1.xml", "<c:chartSpace xmlns:c='x'/>")
        path = Path(self.tmp) / "con_grafico.xlsx"
        path.write_bytes(out.getvalue())
        info = inspect_template(path)
        self.assertTrue(any("gráficos" in r for r in info.risks))


class ValidacionDeCifras(AnalisisCase):
    def test_todas_las_cifras_cuadran_con_su_origen(self):
        run = self.sample_run(agentes=["masivo", "predictivo", "fraudes", "contratos"], parametros={"fecha_cierre": "2025-12-31"})
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        summary = services.validate_figures(run, self.manager)
        self.assertGreater(summary["total"], 50)
        self.assertEqual(summary["no_cuadran"], 0, list(run.cifras.filter(estado="no_cuadra").values_list("fid", "detalle")[:5]))
        self.assertEqual(summary["cambio"], 0)
        self.assertEqual(summary["verificadas"] + summary["sin_origen"], summary["total"])

    def test_un_archivo_de_origen_alterado_se_marca_como_cambio(self):
        run = self.sample_run(agentes=["masivo"])
        doc = run.documentos.get(nombre_original="Auxiliar_proveedores_2025.xlsx")
        with open(doc.archivo.path, "ab") as fh:
            fh.write(b"alterado")
        summary = services.validate_figures(run, self.manager)
        self.assertGreater(summary["cambio"], 0)
        with self.assertRaises(services.ApprovalError):
            services.approve_run(run, self.manager)

    def test_una_cifra_que_no_coincide_con_su_origen_no_cuadra(self):
        run = self.sample_run(agentes=["masivo"])
        c = run.cifras.filter(documento_nombre="Auxiliar_proveedores_2025.xlsx").exclude(filas=[]).first()
        c.valor = c.valor + 5
        c.save()
        summary = services.validate_figures(run, self.manager)
        self.assertGreaterEqual(summary["no_cuadran"], 1)
        c.refresh_from_db()
        self.assertEqual(c.estado, CifraAnalisis.Estado.NO_CUADRA)

    def test_cifra_de_pdf_se_relee_en_su_pagina(self):
        run = self.sample_run(agentes=["masivo"])
        c = run.cifras.get(documento_nombre="Facturas_noviembre.pdf", pagina=1)
        services.validate_figures(run, self.manager)
        c.refresh_from_db()
        self.assertEqual(c.estado, CifraAnalisis.Estado.VERIFICADA)
        self.assertIsNotNone(c.bbox)  # coordenadas para resaltar el importe en la página


class AprobacionYBitacora(AnalisisCase):
    def test_solo_el_jefe_del_proyecto_aprueba(self):
        run = self.sample_run(agentes=["masivo"])
        with self.assertRaises(services.ApprovalError):
            services.approve_run(run, self.auditor)
        with self.assertRaises(services.ApprovalError):
            services.approve_run(run, self.outsider)  # jefe de OTRO proyecto
        services.approve_run(run, self.manager, "Revisado")
        run.refresh_from_db()
        self.assertEqual(run.revision, CorridaAnalisis.Revision.APROBADO)
        self.assertEqual(run.aprobado_por, self.manager)

    def test_rechazar_exige_motivo(self):
        run = self.sample_run(agentes=["masivo"])
        with self.assertRaises(services.ApprovalError):
            services.reject_run(run, self.manager, "  ")
        services.reject_run(run, self.manager, "Falta el saldo del mayor")
        run.refresh_from_db()
        self.assertEqual(run.revision, CorridaAnalisis.Revision.RECHAZADO)

    def test_descartar_un_falso_positivo_exige_motivo(self):
        run = self.sample_run(agentes=["masivo"])
        h = run.hallazgos.first()
        with self.assertRaises(ValueError):
            services.decide_finding(h, self.manager, "descartado", "")
        services.decide_finding(h, self.manager, "descartado", "Ya conciliado con el cliente")
        h.refresh_from_db()
        self.assertEqual(h.decision, "descartado")

    def test_decisiones_bloqueadas_tras_aprobar(self):
        run = self.sample_run(agentes=["masivo"])
        services.approve_run(run, self.manager)
        with self.assertRaises(ValueError):
            services.decide_finding(run.hallazgos.first(), self.manager, "aceptado", "")

    def test_bitacora_encadenada_y_de_solo_agregar(self):
        from analisis.models import BitacoraAnalisis

        run = self.sample_run(agentes=["masivo"])
        self.assertTrue(BitacoraAnalisis.cadena_valida(run))
        self.assertGreaterEqual(run.bitacora.count(), 3)
        first = run.bitacora.first()
        with self.assertRaises(PermissionError):
            first.delete()
        first.accion = "manipulada"
        with self.assertRaises(PermissionError):
            first.save()
        # alterar un registro directamente en la base rompe la cadena
        BitacoraAnalisis.objects.filter(pk=first.pk).update(accion="manipulada")
        self.assertFalse(BitacoraAnalisis.cadena_valida(run))

    def test_csv_con_punto_y_coma_bom_y_sin_inyeccion(self):
        run = self.sample_run(agentes=["masivo"])
        run.hallazgos.update(resultado="=cmd|' /C calc'!A0", procedimiento="+SUMA(1;1)")
        data = services.results_csv(run)
        self.assertTrue(data.startswith("﻿".encode("utf-8")))
        text = data.decode("utf-8-sig")
        self.assertTrue(text.splitlines()[0].startswith("Código;Tipo;Agente"))
        self.assertIn(";'=cmd|", text)  # neutralizado con comilla
        self.assertIn("\"'+SUMA(1;1)\"", text)  # el csv lo entrecomilla por el «;» y queda neutralizado
        self.assertNotIn(";=cmd", text)
