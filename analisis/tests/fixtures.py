"""Archivos de ejemplo idénticos a los del mockup «Cargar ejemplo (PDF + Word + Excel)».

Resultados esperados (guía «4 agentes», §7):
- Factura 1099 (Q 41,610.00) y 1031 cuadran; la 1047 no cuadra por Q 150.00; la 2001 no está
  en el auxiliar.
- Contratos: cláusula de penalización y 6 facturas por Q 47,985.00 registradas después del
  vencimiento (30/06/2025).
"""
from __future__ import annotations

import io
from datetime import date

import docx
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

PROVEEDORES = [
    "Suministros Olmo", "Transportes del Sur", "Gráficas Tormes",
    "Limpiezas Cierzo", "Talleres Bidasoa", "Asesorías Quetzal",
]

FACTURAS_PDF = [
    "FACTURA ELECTRÓNICA FEL\nProveedor: Asesorías Quetzal\nNIT: 7845123-K\nFactura No. 1099\nFecha: 30/11/2025\nServicios de asesoría\nTotal a pagar: Q 41,610.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Gráficas Tormes\nNIT: 5521877-3\nFactura No. 1047\nFecha: 04/03/2025\nImpresión catálogo\nTotal: Q 1,089.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Transportes del Sur\nNIT: 3301456-8\nFactura No. 1031\nFecha: 15/11/2025\nFletes\nTotal: Q 1,447.00",
    "FACTURA ELECTRÓNICA FEL\nProveedor: Servicios Integrales GT\nNIT: 9900112-1\nFactura No. 2001\nFecha: 28/11/2025\nMantenimiento\nTotal: Q 12,480.00",
    "BANCO INDUSTRIAL · ESTADO DE CUENTA\nCuenta monetaria 001-123456-7\nPeríodo: 01/12/2025 al 31/12/2025\nSaldo anterior: Q 98,210.55\nSaldo final: Q 125,430.10",
]

CONTRATO = [
    "CONTRATO DE SERVICIOS PROFESIONALES",
    "Entre Distribuidora Andina, S.A. y Asesorías Quetzal",
    "CLÁUSULA PRIMERA: Objeto: asesoría fiscal",
    "CLÁUSULA TERCERA: Monto total del contrato: Q 150,000.00",
    "CLÁUSULA CUARTA: Vigencia hasta el 30/06/2025",
    "CLÁUSULA OCTAVA: Penalización del 10 % por incumplimiento",
]


def auxiliar_rows() -> list[list]:
    rows = [["Fecha", "Factura", "Proveedor", "Importe"]]
    for i in range(1, 61):
        rows.append([date(2025, i % 12 + 1, 1 + (i * 7) % 28), 1000 + i, PROVEEDORES[i % 6], 800 + (i * 137) % 900])
    rows.append([date(2025, 11, 15), 1031, PROVEEDORES[1], rows[31][3]])
    rows.append([date(2025, 11, 30), 1099, PROVEEDORES[5], 41610])
    return rows


def auxiliar_xlsx(rows: list[list] | None = None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Auxiliar"
    for r in rows or auxiliar_rows():
        ws.append(r)
    for row in ws.iter_rows():
        for cell in row:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.data_type = "s"  # texto que empieza con «=», no una fórmula real
    for cell in ws["A"][1:]:
        cell.number_format = "dd/mm/yyyy"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def auxiliar_csv() -> bytes:
    lines = ["Fecha;Factura;Proveedor;Importe"]
    for r in auxiliar_rows()[1:]:
        lines.append(f"{r[0]:%d/%m/%Y};{r[1]};{r[2]};{r[3]}")
    return "\n".join(lines).encode("utf-8")


def facturas_pdf() -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    for page in FACTURAS_PDF:
        y = 780
        for line in page.split("\n"):
            c.setFont("Helvetica", 12)
            c.drawString(60, y, line)
            y -= 22
        c.showPage()
    c.save()
    return out.getvalue()


def pdf_sin_texto() -> bytes:
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    c.rect(100, 100, 200, 200)
    c.showPage()
    c.save()
    return out.getvalue()


def contrato_docx() -> bytes:
    d = docx.Document()
    for line in CONTRATO:
        d.add_paragraph(line)
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()


def plantilla_xlsx() -> bytes:
    """Papel de trabajo con fórmulas, celda combinada, segunda hoja y datos que NO deben cambiar."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Cédula"
    ws["A1"] = "AUDITA PRO · PAPEL DE TRABAJO"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:D1")
    ws["A2"] = "Cliente: Distribuidora Andina, S.A."
    ws["A3"] = "Cédula: Cuentas por pagar · REF PT CPP-3"
    ws["A4"] = "Período: 31/12/2025"
    ws["A5"] = "Preparó: ________   Revisó: ________"
    ws["A6"] = "Total de control"
    ws["B6"] = 100
    ws["C6"] = "=B6*2"
    ws["A7"] = "RESULTADO"
    ws["A7"].font = Font(bold=True)
    ws2 = wb.create_sheet("Resumen")
    ws2["A1"] = "Resumen"
    ws2["B1"] = "=SUM(1,2,3)"
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
