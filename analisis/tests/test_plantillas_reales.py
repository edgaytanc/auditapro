"""Plantillas reales del Módulo Auditoría (static/templates_base_*): el llenado funciona y advierte lo que no conserva.

La prueba completa sobre las 538 plantillas se ejecuta con ``ANALISIS_SLOW_TESTS=1``; aquí va una muestra
representativa de Financiera, Auditoría Interna y Revisoría Fiscal.
"""
import os
import unittest
from pathlib import Path

from django.conf import settings
from openpyxl import load_workbook

from analisis.engine.template_fill import inspect_template, lost_features
from analisis.models import CorridaAnalisis

from . import fixtures
from .base import AnalisisCase

STATIC = Path(settings.BASE_DIR) / "static"
MUESTRA = [
    "templates_base_financiera/4 PRUEBAS SUSTANTIVAS/9 AUDITORIA CUENTAS POR PAGAR/12_REVISION_DE_FACTURAS_Y_DOCUMENTOS_DE_RESPALDO.xlsx",
    "templates_base_interna/4 PRUEBAS DE PROCESO",
    "templates_base_revisoria/2 EJECUCION/4 CENTRALIZADORA DEL PASIVO.xlsx",
]
CON_FORMA = "templates_base_revisoria/2 EJECUCION/4 CENTRALIZADORA DEL PASIVO.xlsx"


def _resolver(rel: str) -> Path:
    p = STATIC / rel
    return p if p.is_file() else sorted(p.glob("*.xlsx"))[0]


@unittest.skipUnless((STATIC / "templates_base_financiera").is_dir(), "plantillas reales no presentes")
class PlantillasRealesDelModuloAuditoria(AnalisisCase):
    def _llenar(self, path: Path) -> CorridaAnalisis:
        run = self.sample_run(plantilla=self.upload(path.name, path.read_bytes()), agentes=["masivo", "contratos"])
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        return run

    def test_muestra_de_los_tres_modulos_se_llena_sin_tocar_formulas(self):
        for rel in MUESTRA:
            path = _resolver(rel)
            with self.subTest(plantilla=path.name):
                formulas = inspect_template(path).formulas
                run = self._llenar(path)
                v = run.versiones.get(numero=1)
                self.assertEqual(v.informe["formulas_sobrescritas"], 0)
                wb = load_workbook(v.archivo.path)
                self.assertIn("Evidencia", wb.sheetnames)
                self.assertGreaterEqual(inspect_template(v.archivo.path).formulas, formulas)

    def test_advierte_la_forma_dibujada_que_la_copia_no_conserva(self):
        run = self._llenar(STATIC / CON_FORMA)
        warnings = run.versiones.get(numero=1).informe["advertencias"]
        self.assertTrue(any("forma(s) o línea(s) dibujada(s)" in w for w in warnings), warnings)

    def test_sin_perdidas_no_hay_advertencia(self):
        path = _resolver(MUESTRA[0])
        self.assertEqual(lost_features(path, path), [])

    @unittest.skipUnless(os.environ.get("ANALISIS_SLOW_TESTS") == "1", "lenta: todas las plantillas")
    def test_todas_las_plantillas_reales(self):
        from analisis.engine.template_fill import FillError, PasteOptions, fill_template
        from analisis.engine.shared import table_from_dict

        from analisis import services
        from . import fixtures_egresos as fx

        run = self.start(auxiliares=[self.upload("Libro.xlsx", fx.libro_xlsx())],
                         soportes=[self.upload("S.pdf", fx.soportes_pdf())], parametros={"saldo_mayor": str(fx.total_libro())})
        hidden = ("clasificacion", "extraccion", "integracion", "integracion_mes")
        tables = [table_from_dict(run.tablas["tablas"][k]) for k in run.tablas["orden"] if k not in hidden]
        structure = services._structure_data(run, run.tablas)
        out = Path(self.tmp) / "out.xlsx"
        estructuradas = []
        for path in sorted(STATIC.glob("templates_base_*/**/*.xlsx")):
            with self.subTest(plantilla=str(path.relative_to(STATIC))):
                try:
                    r = fill_template(path, out, tables=tables, conclusion="c", summary_line="s", sources_line="f",
                                      evidence_rows=[], evidence_note="", options=PasteOptions(), structure=structure)
                except FillError as exc:
                    self.fail(str(exc))
                self.assertEqual(r.formulas_overwritten, 0)
                if r.structure:
                    estructuradas.append((str(path.relative_to(STATIC)), r.structure["tabla"], r.structure["modo"]))
        print(f"\n{len(estructuradas)} plantillas con tabla de detalle llenada en su estructura:")
        for item in estructuradas:
            print("  ", *item)
