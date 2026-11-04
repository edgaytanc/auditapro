"""Criterio de aceptación de la guía §19: 50,000 filas + un PDF de 100 páginas en menos de 5 minutos.

Es lento, así que solo corre si se pide: ``ANALISIS_SLOW_TESTS=1 python manage.py test analisis.tests.test_performance``.
"""
import io
import os
import random
import time
import tracemalloc
import unittest
from datetime import date, timedelta

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from analisis.models import CorridaAnalisis

from . import fixtures
from .base import AnalisisCase

ROWS = 50_000
PAGES = 100


def big_auxiliar() -> bytes:
    rng = random.Random(7)
    vendors = [f"Proveedor {i:03d}" for i in range(400)]
    wb = Workbook(write_only=True)
    ws = wb.create_sheet("Auxiliar")
    ws.append(["Fecha", "Factura", "Proveedor", "Importe"])
    start = date(2025, 1, 1)
    for i in range(1, ROWS + 1):
        ws.append([start + timedelta(days=rng.randint(0, 364)), 100000 + i, rng.choice(vendors), round(rng.uniform(50, 9000), 2)])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def big_pdf() -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    for p in range(PAGES):
        number = 100000 + (p * 487) % ROWS + 1
        y = 780
        for line in (
            "FACTURA ELECTRÓNICA FEL", f"Proveedor: Proveedor {p % 400:03d}", "NIT: 7845123-K",
            f"Factura No. {number}", "Fecha: 15/06/2025", "Servicios", "Total a pagar: Q 1,234.50",
        ):
            c.drawString(60, y, line)
            y -= 22
        c.showPage()
    c.save()
    return out.getvalue()


@unittest.skipUnless(os.environ.get("ANALISIS_SLOW_TESTS"), "prueba lenta: defina ANALISIS_SLOW_TESTS=1")
class Rendimiento(AnalisisCase):
    def test_50000_filas_y_pdf_de_100_paginas_en_menos_de_5_minutos(self):
        aux, pdf = big_auxiliar(), big_pdf()
        tracemalloc.start()
        t0 = time.perf_counter()
        run = self.start(
            plantilla=self.upload("PT.xlsx", fixtures.plantilla_xlsx()),
            auxiliares=[self.upload("Auxiliar_grande.xlsx", aux)], soportes=[self.upload("Facturas_100.pdf", pdf)],
            agentes=["masivo", "predictivo", "fraudes", "contratos"], parametros={"fecha_cierre": "2025-12-31"},
        )
        elapsed = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        print(f"\n[rendimiento] {ROWS:,} filas + PDF de {PAGES} págs: {elapsed:.1f} s · pico de memoria {peak / 1048576:.0f} MB "
              f"· estado {run.estado} · hallazgos {run.hallazgos.count()} · cifras {run.cifras.count()}")
        self.assertEqual(run.estado, CorridaAnalisis.Estado.TERMINADO, run.error_mensaje)
        self.assertLess(elapsed, 300)
        self.assertEqual(run.documentos.get(nombre_original="Auxiliar_grande.xlsx").filas_leidas, ROWS)
        self.assertEqual(run.documentos.get(nombre_original="Facturas_100.pdf").paginas_leidas, PAGES)
