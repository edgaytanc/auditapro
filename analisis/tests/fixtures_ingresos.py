"""Caso de prueba de ingresos para el papel «9_PRUEBA_DE_INGRESOS» (Financiera · Pruebas sustantivas · Caja y bancos · PT A-11).

Igual que la guía del cliente («Prueba de Ingresos PT A-11»): un reporte de 500 facturas del 01/01/2026 al
31/10/2026 con las columnas No_Factura, No_Recibo, Fecha, NIT, Cliente, Categoria, Subtotal, IVA,
Total_Facturado, Metodo_Cobro, Cuenta_Bancaria_Destino, Referencia_Bancaria y Estado_Cobro; un libro mayor
de 600 partidas y el estado de cuenta bancario de octubre en PDF. Datos de ejemplo (entidad ficticia).

Situaciones que la prueba debe encontrar:
1. Dos facturas iguales el mismo día al mismo cliente (Hotel Brisas del Lago, Q 18,816.00 cada una).
2. Dos facturas atípicas por su tamaño (Q 285,600.00 y Q 312,480.00).
3. Tres facturas emitidas en sábado o domingo.
4. Una factura por monto redondo alto (Q 50,000.00) a un cliente ocasional.
5. Facturas pendientes de cobro (sin referencia bancaria: «N/A»).
6. Falta la factura FC-2026-00347 (salto en la numeración: una factura anulada o no registrada).
"""
from __future__ import annotations

import io
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

HEAD = ["No_Factura", "No_Recibo", "Fecha", "NIT", "Cliente", "Categoria", "Subtotal", "IVA", "Total_Facturado",
        "Metodo_Cobro", "Cuenta_Bancaria_Destino", "Referencia_Bancaria", "Estado_Cobro"]
CENTRAL = "Banco Cuenta Monetaria Central"
RECAUDADORA = "Banco Cuenta Recaudadora Secundaria"
CLIENTES = [
    ("Ferretería La Unión, S.A.", "1029384-5"), ("Constructora Altamira, S.A.", "2938475-1"), ("Agroservicios El Valle", "3847561-2"),
    ("Hotel Brisas del Lago", "4756123-9"), ("Distribuidora Santa Ana", "5612398-7"), ("Supermercados La Económica", "6123987-4"),
    ("Clínica San Rafael", "7239846-0"), ("Colegio Monte Verde", "8398471-6"), ("Transportes Rápidos del Sur", "9384712-3"),
    ("Industrias Textiles Maya", "1847293-8"), ("Panificadora La Espiga", "2749381-5"), ("Restaurante El Fogón", "3491827-2"),
    ("Municipalidad de San Lucas", "4918273-K"), ("Cooperativa Integral El Progreso", "5182736-1"), ("Farmacias Salud Total", "6827351-9"),
    ("Grupo Inmobiliario Horizonte", "7273518-4"), ("Automotriz del Pacífico", "8735182-6"), ("Café Finca Las Nubes", "9351827-0"),
]
CATEGORIAS = ["Venta de mercadería", "Servicios de instalación", "Mantenimiento", "Repuestos y accesorios"]
METODOS = ["Transferencia Bancaria", "Cheque de Caja", "Depósito Monetario", "Tarjeta de Crédito"]
Q = Decimal("0.01")


def _q(x) -> Decimal:
    return Decimal(str(x)).quantize(Q, rounding=ROUND_HALF_UP)


def _business_days() -> list[date]:
    d, out = date(2026, 1, 2), []
    while d <= date(2026, 10, 31):
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def facturas() -> list[list]:
    """Las 500 facturas en orden de fecha (No_Factura correlativo)."""
    rnd = random.Random(2026)
    days = _business_days()
    dates = sorted(rnd.choice(days) for _ in range(493))
    rows: list[dict] = []
    for d in dates:
        cliente, nit = rnd.choice(CLIENTES)
        sub = _q(rnd.lognormvariate(8.9, 0.55))
        rows.append({"fecha": d, "cliente": cliente, "nit": nit, "sub": sub})
    # 1) duplicado: misma factura dos veces el mismo día
    dup = rows[211]
    dup["cliente"], dup["nit"], dup["sub"] = "Hotel Brisas del Lago", "4756123-9", _q("16800.00")
    rows.insert(212, dict(dup))
    # 2) atípicas por tamaño
    rows.insert(300, {"fecha": date(2026, 6, 15), "cliente": "Grupo Inmobiliario Horizonte", "nit": "7273518-4", "sub": _q("255000.00")})
    rows.insert(410, {"fecha": date(2026, 8, 27), "cliente": "Constructora Altamira, S.A.", "nit": "2938475-1", "sub": _q("279000.00")})
    # 3) fines de semana
    for d, k in ((date(2026, 3, 14), 130), (date(2026, 5, 24), 240), (date(2026, 9, 19), 455)):
        cliente, nit = CLIENTES[k % len(CLIENTES)]
        rows.insert(k, {"fecha": d, "cliente": cliente, "nit": nit, "sub": _q(rnd.lognormvariate(8.9, 0.4))})
    # 4) monto redondo alto a un cliente ocasional (total exacto Q 50,000.00)
    rows.insert(350, {"fecha": date(2026, 7, 10), "cliente": "Eventos y Convenciones Quetzal", "nit": "1112223-4",
                      "sub": _q(Decimal("50000") / Decimal("1.12")), "total": _q("50000.00")})
    rows = rows[:500]
    rows.sort(key=lambda r: r["fecha"])
    out = []
    for i, r in enumerate(rows, start=1):
        sub = r["sub"]
        total = r.get("total") or _q(sub * Decimal("1.12"))
        iva = total - sub
        pending = (i % 11 == 0) or r["fecha"] >= date(2026, 10, 27)
        metodo = METODOS[(i * 7) % len(METODOS)]
        cuenta = CENTRAL if i % 3 else RECAUDADORA
        out.append([
            f"FC-2026-{i + (i >= 347):05d}", "" if pending else f"RC-2026-{i:05d}", r["fecha"].strftime("%d/%m/%Y"), r["nit"], r["cliente"],
            CATEGORIAS[(i * 5) % len(CATEGORIAS)], f"{sub:.2f}", f"{iva:.2f}", f"{total:.2f}", metodo, cuenta,
            "N/A" if pending else f"TRX-{7340000 + i * 37}", "Pendiente de Cobro" if pending else "Cobrado",
        ])
    return out


def total_facturado() -> Decimal:
    return sum((Decimal(r[8]) for r in facturas()), Decimal(0))


def ingresos_csv() -> bytes:
    lines = [",".join(HEAD)]
    for r in facturas():
        lines.append(",".join(f'"{v}"' if "," in str(v) else str(v) for v in r))
    return "\n".join(lines).encode("utf-8")


def mayor_csv() -> bytes:
    """Libro mayor de 600 partidas (no es el auxiliar de la prueba: no tiene facturas ni bancos)."""
    rnd = random.Random(530)
    cuentas = [("4101", "Ventas de mercadería"), ("4102", "Ingresos por servicios"), ("1101", "Caja general"),
               ("1102", "Bancos"), ("2101", "Proveedores"), ("5101", "Costo de ventas"), ("6101", "Gastos de administración")]
    lines = ["Fecha,No_Partida,Codigo_Cuenta,Nombre_Cuenta,Descripcion,Debe,Haber"]
    days = _business_days()
    for i in range(1, 601):
        d = rnd.choice(days)
        code, name = rnd.choice(cuentas)
        amount = _q(rnd.lognormvariate(10.2, 0.9))
        debe, haber = (amount, Decimal(0)) if i % 2 else (Decimal(0), amount)
        lines.append(f"{d:%d/%m/%Y},PD-{i:04d},{code},{name},Registro contable {i},{debe:.2f},{haber:.2f}")
    return "\n".join(lines).encode("utf-8")


def estado_cuenta_pdf() -> bytes:
    """Estado de cuenta de octubre 2026 (depósitos de algunas facturas cobradas)."""
    cobradas = [r for r in facturas() if r[2].endswith("/10/2026") and r[12] == "Cobrado"][:12]
    out = io.BytesIO()
    c = canvas.Canvas(out, pagesize=A4)
    y = 790
    for line in ["BANCO METROPOLITANO", "ESTADO DE CUENTA - OCTUBRE 2026",
                 "Titular: Comercializadora del Valle, S.A.   NIT 8493021-4",
                 "Banco Cuenta Monetaria Central 01-0234567-8", "Saldo inicial al 01/10/2026: Q 145,280.00", ""]:
        c.setFont("Helvetica-Bold" if y > 760 else "Helvetica", 12)
        c.drawString(60, y, line)
        y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(60, y, "Fecha        Referencia        Descripción                          Depósito")
    y -= 16
    for r in cobradas:
        c.drawString(60, y, f"{r[2]}   {r[11]}   Depósito {r[0]} {r[4][:22]}   Q {Decimal(r[8]):,.2f}")
        y -= 15
    y -= 10
    total = sum(Decimal(r[8]) for r in cobradas)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, f"Total depósitos: Q {total:,.2f}")
    c.drawString(60, y - 18, f"Saldo final al 31/10/2026: Q {Decimal('145280.00') + total:,.2f}")
    c.showPage()
    c.save()
    return out.getvalue()
