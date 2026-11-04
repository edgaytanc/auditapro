"""Caso de prueba de gastos para el papel «10_INTEGRACION_EGRESOS» (Financiera · Caja y bancos · A-12).

Libro de egresos 2025 de Distribuidora Andina, S.A. (70 partidas) con pagos recurrentes normales y estas
situaciones que una prueba de gastos debe encontrar:

1. Combustibles Petro: el mismo pago de Q 8,750.00 dos veces (14/03 y 17/03, cheques distintos).
2. Servicios Varios López: dos pagos de Q 9,850.00 y Q 9,975.00 (20 y 21/06; el 21 es sábado), justo bajo el
   límite de autorización de Q 10,000.00.
3. Fundación Esperanza: un pago único y alto de Q 25,000.00 (monto redondo, proveedor ocasional).
4. Taller El Rápido: la factura 5521 dice Q 3,480.00 y el libro registra Q 3,840.00 (diferencia Q 360.00).
5. Eventos Premium: factura 7710 por Q 6,300.00 que no está en el libro de egresos.
6. Inmobiliaria Los Arcos: alquiler pagado de octubre a diciembre con el contrato vencido el 30/09/2025.

El alquiler (Q 15,000.00) y los honorarios (Q 4,500.00) se repiten cada mes y NO deben salir como duplicados.
"""
from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import docx
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HEAD = ["Fecha", "Tipo doc.", "No. documento", "Proveedor (beneficiario)", "Concepto", "Cuenta contable", "Monto"]
LOS_ARCOS = "Inmobiliaria Los Arcos, S.A."


def _habil(d: date) -> date:
    """Los pagos programados caen en día hábil (si el día fijo es sábado o domingo, se paga el lunes)."""
    while d.weekday() >= 5:
        d = d.fromordinal(d.toordinal() + 1)
    return d


def libro_rows() -> list[list]:
    rows: list[list] = []

    def add(d, tipo, prov, concepto, cuenta, monto, habil=True):
        rows.append([_habil(d) if habil else d, tipo, "", prov, concepto, cuenta, Decimal(str(monto))])

    luz = [3215.40, 3398.75, 3120.10, 3540.65, 3611.20, 3702.95, 3655.30, 3590.85, 3488.40, 3376.15, 3299.60, 3712.45]
    tel = [1185.50, 1192.30, 1210.25, 1198.70, 1203.90, 1215.35, 1188.45, 1226.80, 1209.15, 1197.60, 1214.05, 1231.40]
    for m in range(1, 13):
        add(date(2025, m, 5), "Cheque", LOS_ARCOS, f"Alquiler de oficinas {m:02d}/2025", "6110 Arrendamientos", 15000)
        add(date(2025, m, 8), "Transferencia", "Consultores Asociados GT", f"Honorarios contables {m:02d}/2025", "6105 Servicios profesionales", 4500)
        add(date(2025, m, 12), "Transferencia", "EEGSA", f"Energía eléctrica {m:02d}/2025", "6120 Servicios básicos", luz[m - 1])
        add(date(2025, m, 16), "Transferencia", "Claro Guatemala", f"Telefonía e internet {m:02d}/2025", "6120 Servicios básicos", tel[m - 1])
    for d, monto in [(date(2025, 1, 22), 612.30), (date(2025, 3, 27), 845.10), (date(2025, 5, 23), 530.75),
                     (date(2025, 7, 24), 918.40), (date(2025, 9, 25), 702.15), (date(2025, 11, 26), 1146.90)]:
        add(d, "Cheque", "Librería y Papelería Sumario", "Útiles de oficina", "6140 Papelería y útiles", monto)
    for d, monto in [(date(2025, 2, 18), 2150.00 + 85.5), (date(2025, 5, 14), 1890.25), (date(2025, 8, 20), 3840.00),
                     (date(2025, 11, 19), 2975.60)]:
        add(d, "Cheque", "Taller El Rápido", "Mantenimiento de vehículos", "6130 Mantenimiento", monto)
    for d, monto in [(date(2025, 4, 10), 7850.00 + 125), (date(2025, 7, 15), 6420.80), (date(2025, 10, 9), 8135.45)]:
        add(d, "Transferencia", "Medios Creativos", "Publicidad en medios", "6150 Publicidad", monto)
    for d, monto in [(date(2025, 1, 29), 6215.35), (date(2025, 3, 14), 8750.00), (date(2025, 3, 16), 8750.00),
                     (date(2025, 6, 11), 7020.60), (date(2025, 9, 17), 7488.20), (date(2025, 12, 10), 7930.15)]:
        add(d, "Cheque", "Distribuidora de Combustibles Petro", "Combustible flotilla", "6160 Combustibles", monto)
    add(date(2025, 6, 20), "Transferencia", "Servicios Varios López", "Servicios de limpieza y fumigación", "6130 Mantenimiento", 9850)
    add(date(2025, 6, 21), "Transferencia", "Servicios Varios López", "Servicios de limpieza y fumigación", "6130 Mantenimiento", 9975,
        habil=False)  # sábado
    add(date(2025, 12, 18), "Cheque", "Fundación Esperanza", "Donación", "6190 Donaciones", 25000)
    rows.sort(key=lambda r: (r[0], r[3]))
    chq, trf = 4100, 900  # chequera y transferencias numeradas en orden de fecha, como en el banco
    for r in rows:
        if r[1] == "Cheque":
            chq += 1
            r[2] = str(chq)
        else:
            trf += 1
            r[2] = f"TRF-{trf}"
    return rows


def total_libro() -> Decimal:
    return sum((r[6] for r in libro_rows()), Decimal(0))


def libro_xlsx() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Libro de egresos"
    ws.append(HEAD)
    for r in libro_rows():
        ws.append([r[0], r[1], r[2], r[3], r[4], r[5], float(r[6])])
    for row in ws.iter_rows(min_row=2):
        row[0].number_format = "dd/mm/yyyy"
        row[6].number_format = "#,##0.00"
    for col, w in zip("ABCDEFG", (12, 14, 14, 34, 36, 28, 14)):
        ws.column_dimensions[col].width = w
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


SOPORTES = [
    "FACTURA ELECTRÓNICA FEL\nProveedor: Inmobiliaria Los Arcos, S.A.\nNIT: 2245781-6\nFactura No. 3105\nFecha: 05/03/2025\nAlquiler de oficinas marzo 2025\nTotal: Q 15,000.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Distribuidora de Combustibles Petro\nNIT: 6612034-1\nFactura No. 88213\nFecha: 14/03/2025\nCombustible flotilla\nTotal: Q 8,750.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Taller El Rápido\nNIT: 4478120-9\nFactura No. 5521\nFecha: 20/08/2025\nMantenimiento de vehículos\nTotal: Q 3,480.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Consultores Asociados GT\nNIT: 8890451-2\nFactura No. 1207\nFecha: 08/07/2025\nHonorarios contables julio 2025\nTotal: Q 4,500.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Eventos Premium\nNIT: 3019876-4\nFactura No. 7710\nFecha: 12/08/2025\nEvento de aniversario\nTotal: Q 6,300.00",
]

CONTRATO_ARRENDAMIENTO = [
    "CONTRATO DE ARRENDAMIENTO DE OFICINAS",
    "Entre Distribuidora Andina, S.A. y Inmobiliaria Los Arcos, S.A.",
    "CLÁUSULA PRIMERA: Objeto: arrendamiento del local de oficinas, zona 10, Ciudad de Guatemala",
    "CLÁUSULA TERCERA: Monto total del contrato: Q 180,000.00 (renta mensual de Q 15,000.00)",
    "CLÁUSULA CUARTA: Vigencia hasta el 30/09/2025",
    "CLÁUSULA SÉPTIMA: Penalización por terminación anticipada equivalente a dos meses de renta",
]


def soportes_pdf() -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    for page in SOPORTES:
        y = 780
        for line in page.split("\n"):
            c.setFont("Helvetica", 12)
            c.drawString(60, y, line)
            y -= 22
        c.showPage()
    c.save()
    return out.getvalue()


def contrato_docx() -> bytes:
    d = docx.Document()
    for line in CONTRATO_ARRENDAMIENTO:
        d.add_paragraph(line)
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()
