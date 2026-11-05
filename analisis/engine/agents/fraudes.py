"""Agente Detección de fraudes (NIA 240 · 330).

Busca señales de riesgo sobre el 100 % de las partidas. Una señal NO demuestra fraude: es
un indicador que el auditor debe investigar (NIA 240).
"""
from __future__ import annotations

import math
import re
from decimal import Decimal

from ..normalize import fmt_money, fmt_pct, q2
from ..shared import AgentOutput, Table
from .common import ALTA, BAJA, MEDIA, AgentContext, AgentError, finding, sum_amounts

AGENT = "fraudes"
BENFORD = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
CHI2_CRITICAL_5PCT_8DF = 15.51
BENFORD_MIN_N = 300


def first_digit(amount: Decimal) -> int | None:
    text = f"{abs(amount):f}".lstrip("0.")
    return int(text[0]) if text and text[0].isdigit() and text[0] != "0" else None


def benford(amounts: list[Decimal]) -> tuple[int, float]:
    counts = [0] * 9
    for a in amounts:
        d = first_digit(a)
        if d:
            counts[d - 1] += 1
    n = sum(counts)
    if not n:
        return 0, 0.0
    chi = sum((o - n * e / 100) ** 2 / (n * e / 100) for o, e in zip(counts, BENFORD))
    return n, chi


def _numeric_part(raw: str) -> int | None:
    digits = re.sub(r"\D", "", raw or "")
    return int(digits) if digits else None


def _close_repeats(rows: list) -> list:
    """Filas de un pago recurrente que sí se repiten: mismo documento o fechas a 10 días o menos."""
    out = []
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            same_doc = a.doc and a.doc == b.doc
            close = a.date and b.date and abs((a.date - b.date).days) <= 10
            if same_doc or close:
                out += [x for x in (a, b) if x not in out]
    return out


def run(ctx: AgentContext) -> AgentOutput:
    valued = [r for r in ctx.rows if r.amount is not None]
    if not valued:
        raise AgentError("El auxiliar no tiene importes reconocibles en la columna elegida.")
    # Ingresos: las facturas las emite la entidad. El límite de autorización es de pagos (solo si el auditor lo indica)
    # y la numeración consecutiva es lo normal; lo que se prueba es que no haya saltos (correlatividad).
    own_docs = ctx.params.get("tipo_papel") == "ingresos"
    limite = ctx.param_decimal("limite_autorizacion", "10000")
    if own_docs and ctx.params.get("limite_autorizacion") in (None, ""):
        limite = Decimal(0)
    z_threshold = ctx.param_float("z", 3.0)
    multiplo = ctx.param_decimal("multiplo_redondo", "1000")

    n = len(valued)
    total = sum_amounts(valued)
    mean = float(total) / n
    sd = math.sqrt(sum((float(r.amount) - mean) ** 2 for r in valued) / n) or 0.0

    signals: list[tuple[str, object, str]] = []  # (indicador, fila, detalle)
    dup_groups: dict[tuple, list] = {}
    for r in valued:
        dup_groups.setdefault((r.group, r.amount), []).append(r)
    # Pago recurrente (alquiler, honorario fijo, planilla): mismo grupo e importe en 3 meses distintos o más.
    # No es una señal de duplicado ni de «monto redondo»; se informa aparte.
    recurrent = {
        key for key, rows in dup_groups.items()
        if len({(r.date.year, r.date.month) for r in rows if r.date}) >= 3
    }
    duplicates = []
    for key, rows in dup_groups.items():
        if len(rows) < 2:
            continue
        if key in recurrent:
            # dentro de un pago recurrente, solo es duplicado lo que repite documento o cae en el mismo período corto
            rows = _close_repeats(rows)
            if len(rows) < 2:
                continue
        duplicates.append(rows)
    for rows in duplicates:
        for r in rows:
            signals.append(("Posible duplicado", r, f"mismo {ctx.group_header.lower()} e importe"))
    atypical = []
    if sd:
        for r in valued:
            z = (float(r.amount) - mean) / sd
            if abs(z) > z_threshold:
                atypical.append(r)
                signals.append(("Importe atípico", r, f"z = {z:.1f}"))
    rounds = [r for r in valued if multiplo > 0 and r.amount >= multiplo and r.amount % multiplo == 0
              and (r.group, r.amount) not in recurrent]
    for r in rounds:
        signals.append(("Monto redondo", r, f"múltiplo exacto de {multiplo:,.0f}"))
    weekends = [r for r in valued if r.date and r.date.weekday() >= 5]
    for r in weekends:
        signals.append(("Fin de semana", r, r.date.strftime("%d/%m/%Y")))

    order = {"Posible duplicado": 0, "Importe atípico": 1, "Monto redondo": 2, "Fin de semana": 3}
    signals.sort(key=lambda s: (order[s[0]], -s[1].amount))

    main = Table(
        key="analisis",
        title=f"Señales de riesgo sobre el 100 % de {n:,} partidas",
        head=["Indicador", "Grupo", "Importe", "Detalle", "Ref. origen"],
        flagged=bool(signals),
    )
    for indicator, row, detail in signals:
        main.add([indicator, row.group, ctx.fig_row(row), detail, ctx.ref_rows([row])], "warn")
    benford_n, chi = benford([r.amount for r in valued])
    if benford_n < BENFORD_MIN_N:
        reading = "muestra pequeña: referencial"
    elif chi > CHI2_CRITICAL_5PCT_8DF:
        reading = "desviación significativa"
    else:
        reading = "sin desviación"
    main.add(["Ley de Benford", f"{benford_n:,} partidas", "", f"χ² = {chi:.1f} · {reading}", f"{ctx.source_name} · 100 %"], "total")
    main.cap()
    notes = []
    if main.truncated:
        notes.append(f"Se muestran las señales de mayor importe; {main.truncated:,} señales menores se omiten (los conteos las incluyen).")
    if recurrent:
        names = ", ".join(sorted({g for g, _ in recurrent})[:4])
        notes.append(f"Pagos recurrentes ({names}): mismo {ctx.group_header.lower()} e importe cada mes; no se tratan como duplicados "
                     "ni como montos redondos, salvo que repitan documento o caigan a 10 días o menos.")
    main.note = " ".join(notes)

    out = AgentOutput(agent=AGENT, main=main)
    out.exceptions = len(signals)

    # -- pruebas adicionales
    extra_rows: list[tuple[str, str, object, str, str]] = []  # indicador, grupo, importe, detalle, ref
    bajo = [r for r in valued if limite > 0 and limite * Decimal("0.9") <= r.amount < limite]
    for r in bajo:
        extra_rows.append(("Bajo el límite de autorización", r.group, ctx.fig_row(r), f"{fmt_pct(r.amount / limite)} del límite", ctx.ref_rows([r])))
    consecutivos = []
    doc_header = ctx.headers[ctx.cols.doc] if 0 <= ctx.cols.doc < len(ctx.headers) else ""
    # La numeración consecutiva de un PROVEEDOR (sus facturas) es señal de proveedor ficticio. La de nuestros propios
    # cheques o transferencias es normal: si la columna no es de facturas del proveedor, la prueba no aplica.
    supplier_docs = not own_docs and bool(re.search(r"factura|fact\b|invoice|serie|dte|fel", doc_header, re.I))
    saltos: list[tuple[int, int]] = []
    issued: list[int] = []
    if ctx.cols.doc >= 0 and own_docs:
        issued = sorted({x for x in (_numeric_part(r.doc_raw) for r in valued) if x is not None})
        saltos = [(a, b) for a, b in zip(issued, issued[1:]) if b - a > 1]
    if ctx.cols.doc >= 0 and supplier_docs:
        by_group: dict[str, list] = {}
        for r in valued:
            num = _numeric_part(r.doc_raw)
            if num is not None:
                by_group.setdefault(r.group, []).append((num, r))
        for group, items in by_group.items():
            items.sort(key=lambda t: t[0])
            for (a, ra), (b, rb) in zip(items, items[1:]):
                if b - a == 1:
                    consecutivos.append((group, ra, rb))
                    extra_rows.append(("Numeración consecutiva", group, ctx.fig_row(rb), f"docs {a} y {b}", ctx.ref_rows([ra, rb])))
    occasional = []
    by_vendor: dict[str, list] = {}
    for r in valued:
        by_vendor.setdefault(r.group, []).append(r)
    for group, rows in by_vendor.items():
        if len(rows) == 1 and mean > 0 and float(rows[0].amount) > mean * 3:
            occasional.append(rows[0])
            extra_rows.append(
                ("Cliente ocasional con factura alta" if own_docs else "Proveedor ocasional con pago alto", group, ctx.fig_row(rows[0]),
                 f"1 sola {'factura' if own_docs else 'pago'}, {float(rows[0].amount) / mean:.1f} veces la media".replace("1 sola pago", "1 solo pago"),
                 ctx.ref_rows(rows))
            )
    sin_registro = [c for c in ctx.cruce if c.estado == "no_cuadra" and c.motivo.startswith("Documento sin registro")]
    for c in sin_registro:
        extra_rows.append(("Documento fuera del auxiliar", c.proveedor, c.total, f"Documento {c.numero or '(s/n)'} sin registro", f"{c.doc_name} · pág. {c.page}"))

    extra = Table(
        key="extra:fraude",
        title="Pruebas adicionales de fraude",
        head=["Indicador", "Grupo", "Importe", "Detalle", "Ref. origen"],
        flagged=bool(extra_rows),
    )
    for item in extra_rows:
        extra.add(list(item), "warn")
    if not extra_rows:
        extra.add(["Sin hallazgos adicionales", "", "", "", ctx.source_name])
    if own_docs and issued:
        extra.note = (f"Correlatividad de las facturas emitidas («{doc_header}»): {len(issued):,} números, del {issued[0]} al "
                      f"{issued[-1]}, " + ("sin saltos." if not saltos else f"con {len(saltos)} salto(s): "
                                          + ", ".join(f"{a} → {b}" for a, b in saltos[:5]) + ".")
                      + " La numeración consecutiva de un proveedor no aplica: son facturas de la entidad.")
    elif ctx.cols.doc >= 0 and not supplier_docs:
        extra.note = (f"Numeración consecutiva: no aplica, la columna «{doc_header}» no es de facturas del proveedor "
                      "(cheques o transferencias propios van en secuencia).")
    extra.cap()
    out.extras.append(extra)
    out.exceptions += len(extra_rows)

    # -- riesgos y hallazgos
    if duplicates:
        at_risk = sum(((len(rows) - 1) * rows[0].amount for rows in duplicates), Decimal(0))
        out.findings.append(
            finding(
                AGENT, "hallazgo", "Partidas repetidas",
                f"{sum(len(r) for r in duplicates)} partidas repetidas ({len(duplicates)} grupo(s) con el mismo {ctx.group_header.lower()} e importe)",
                ALTA, importe=q2(at_risk), nia="NIA 240 · 330", aseveracion="Ocurrencia · Exactitud",
                condicion=f"{sum(len(r) for r in duplicates)} partidas con igual {ctx.group_header.lower()} e importe",
                criterio="NIA 240: indicador de fraude o error · NIA 330: respuesta sobre partidas inusuales",
                causa="Por confirmar con la gerencia (doble registro, doble pago o fraccionamiento)",
                efecto=f"{fmt_money(q2(at_risk))} potencialmente duplicado",
                recomendacion="Pedir ambos soportes y el comprobante de pago; si es duplicado, recuperar y proponer ajuste (NIA 450)",
                origen=ctx.ref_rows(duplicates[0]),
            )
        )
        out.findings.append(
            finding(AGENT, "riesgo", "Pagos o registros duplicados",
                    f"{sum(len(r) for r in duplicates)} partidas en {len(duplicates)} grupo(s)", ALTA,
                    nia="NIA 240 · 330", aseveracion="Ocurrencia · Exactitud", origen=ctx.ref_rows(duplicates[0]),
                    recomendacion="Verificar con soporte original y pago bancario (NIA 330)")
        )
    if atypical:
        out.findings.append(
            finding(AGENT, "hallazgo", "Importes atípicos",
                    f"{len(atypical)} importes con |z| > {z_threshold:g}", MEDIA, importe=sum_amounts(atypical),
                    nia="NIA 240 · 520", aseveracion="Ocurrencia · Valuación",
                    condicion=f"{len(atypical)} partidas lejos de la media de la población",
                    criterio="NIA 240: transacciones inusuales · NIA 520: investigar lo que difiere de lo esperado",
                    efecto=fmt_money(sum_amounts(atypical)),
                    recomendacion="Pedir soporte y aprobación de cada partida atípica",
                    origen=ctx.ref_rows(atypical))
        )
    if rounds:
        out.findings.append(
            finding(AGENT, "hallazgo", "Montos redondos",
                    f"{len(rounds)} importes múltiplos exactos de {multiplo:,.0f}", BAJA, importe=sum_amounts(rounds),
                    nia="NIA 240", aseveracion="Valuación",
                    condicion=f"{len(rounds)} importes múltiplos exactos de {multiplo:,.0f}",
                    criterio="NIA 240: indicador analítico (por sí solo no prueba nada)",
                    causa="Por confirmar con la gerencia (pagos fijos, anticipos o estimaciones)",
                    efecto=fmt_money(sum_amounts(rounds)), recomendacion="Pedir soporte de los de mayor importe",
                    origen=ctx.ref_rows(rounds))
        )
    if weekends:
        out.findings.append(
            finding(AGENT, "hallazgo", "Partidas en fin de semana",
                    f"{len(weekends)} partidas fechadas en sábado o domingo", BAJA, importe=sum_amounts(weekends),
                    nia="NIA 240", aseveracion="Ocurrencia",
                    condicion=f"{len(weekends)} partidas fechadas en sábado o domingo",
                    criterio="NIA 240: asientos o transacciones fuera del horario habitual",
                    causa="Por confirmar con la gerencia (operación en día no hábil o fecha de captura)",
                    efecto=fmt_money(sum_amounts(weekends)), recomendacion="Verificar quién registró y aprobó",
                    origen=ctx.ref_rows(weekends))
        )
    if bajo:
        out.findings.append(
            finding(AGENT, "hallazgo", "Importes justo bajo el límite de autorización",
                    f"{len(bajo)} partidas entre 90 % y 99.9 % del límite de autorización ({fmt_money(limite)})", ALTA,
                    importe=sum_amounts(bajo), nia="NIA 240 · 315 · 265", aseveracion="Ocurrencia · Autorización",
                    condicion=f"{len(bajo)} partidas entre 90 % y 99.9 % del límite de {fmt_money(limite)}",
                    criterio="NIA 240 · NIA 315: control de autorización · NIA 265: comunicar deficiencias",
                    causa="Por confirmar con la gerencia (fraccionamiento para evitar una aprobación superior)",
                    efecto=fmt_money(sum_amounts(bajo)),
                    recomendacion="Revisar quién aprobó y si hay pagos fraccionados al mismo proveedor",
                    origen=ctx.ref_rows(bajo))
        )
        out.findings.append(
            finding(AGENT, "riesgo", "Elusión del control de autorización por fraccionamiento",
                    f"{len(bajo)} partidas justo bajo el límite", ALTA, nia="NIA 315 · 265 · 240",
                    aseveracion="Ocurrencia · Autorización", origen=ctx.ref_rows(bajo),
                    recomendacion="Probar el control de autorización y comunicar la deficiencia a la gerencia (NIA 265)")
        )
    if saltos:
        missing = sum(b - a - 1 for a, b in saltos)
        out.findings.append(
            finding(AGENT, "hallazgo", "Correlatividad de las facturas emitidas (atributo 3)",
                    f"{missing} número(s) de factura faltantes en {len(saltos)} salto(s) de la numeración", MEDIA,
                    nia="NIA 500 · 330", aseveracion="Integridad",
                    condicion=f"Saltos en la numeración: " + ", ".join(f"{a} → {b}" for a, b in saltos[:5]),
                    criterio="Las facturas emitidas deben ser correlativas y las anuladas, conservarse",
                    causa="Por confirmar con la gerencia (facturas anuladas o no registradas)",
                    efecto=f"{missing} factura(s) sin registro en el reporte de ingresos",
                    recomendacion="Obtener las facturas anuladas o faltantes y confirmar que no son ventas sin registrar",
                    origen=ctx.source_name)
        )
    if consecutivos:
        out.findings.append(
            finding(AGENT, "hallazgo", "Numeración consecutiva del mismo proveedor",
                    f"{len(consecutivos)} casos de documentos consecutivos del mismo proveedor", MEDIA,
                    importe=sum_amounts([c[2] for c in consecutivos]), nia="NIA 240 · 330",
                    condicion=f"{len(consecutivos)} casos de documentos consecutivos",
                    criterio="NIA 240 · NIA 330", causa="Por confirmar con la gerencia (un solo servicio fraccionado)",
                    efecto=fmt_money(sum_amounts([c[2] for c in consecutivos])),
                    recomendacion="Revisar si es un solo servicio dividido en varias facturas",
                    origen=ctx.ref_rows([consecutivos[0][1], consecutivos[0][2]]))
        )
    if occasional and own_docs:
        out.findings.append(
            finding(AGENT, "hallazgo", "Clientes ocasionales con una sola factura alta",
                    f"{len(occasional)} cliente(s) ocasional(es) con una sola factura alta", MEDIA, importe=sum_amounts(occasional),
                    nia="NIA 240 · 500", aseveracion="Ocurrencia",
                    condicion=f"{len(occasional)} cliente(s) con una única factura mayor a 3 veces la media",
                    criterio="NIA 240: ventas ficticias o no recurrentes · NIA 500",
                    causa="Por confirmar con la gerencia (venta puntual o cliente sin soporte)",
                    efecto=fmt_money(sum_amounts(occasional)),
                    recomendacion="Validar la existencia del cliente (NIT), la entrega y el cobro de la factura",
                    origen=ctx.ref_rows(occasional))
        )
    elif occasional:
        out.findings.append(
            finding(AGENT, "hallazgo", "Proveedores ocasionales con un solo pago alto",
                    f"{len(occasional)} proveedores ocasionales con un solo pago alto", MEDIA, importe=sum_amounts(occasional),
                    nia="NIA 240 · 500", aseveracion="Existencia",
                    condicion=f"{len(occasional)} proveedores con un único pago mayor a 3 veces la media",
                    criterio="NIA 240: proveedores ficticios o no recurrentes · NIA 500",
                    causa="Por confirmar con la gerencia (compra puntual o proveedor sin soporte)",
                    efecto=fmt_money(sum_amounts(occasional)),
                    recomendacion="Validar existencia del proveedor (NIT, domicilio) y la entrega del bien o servicio",
                    origen=ctx.ref_rows(occasional))
        )
    if not out.findings:
        out.findings.append(
            finding(AGENT, "riesgo",
                    "Sin señales de fraude en el 100 % revisado; la presunción de elusión de controles por la dirección sigue vigente",
                    "Ningún indicador activo", BAJA, nia="NIA 240", origen=ctx.source_name,
                    recomendacion="Mantener los procedimientos de asientos manuales y estimaciones (NIA 240)")
        )

    out.conclusion = (
        f"Se recorrió el 100 % de {n:,} partidas. Indicadores de riesgo encontrados: {len(signals) + len(extra_rows)}. "
        "Son señales que el auditor debe investigar, no conclusiones de fraude (NIA 240)."
    )
    return out
