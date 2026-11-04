"""Agente Datos masivos (NIA 500 · 530).

Prueba principal: sumaria del 100 % del auxiliar por grupo. Pruebas adicionales:
estadísticas de la población, partidas mayores (top 10), cuadre contra el mayor y corte
alrededor del cierre.
"""
from __future__ import annotations

import math
from datetime import timedelta
from decimal import Decimal

from ..normalize import fmt_money, fmt_num, fmt_pct, q2
from ..shared import AgentOutput, Fig, Table
from .common import ALTA, BAJA, MEDIA, AgentContext, AgentError, finding, sum_amounts

AGENT = "masivo"
CORTE_DIAS = 10


def run(ctx: AgentContext) -> AgentOutput:
    threshold = ctx.param_decimal("umbral_concentracion", "30") / 100
    valued = [r for r in ctx.rows if r.amount is not None]
    if not valued:
        raise AgentError("El auxiliar no tiene importes reconocibles en la columna elegida.")
    total = sum_amounts(valued)

    groups: dict[str, list] = {}
    for row in valued:
        groups.setdefault(row.group or "(sin dato)", []).append(row)
    ordered = sorted(groups.items(), key=lambda kv: sum_amounts(kv[1]), reverse=True)

    main = Table(
        key="analisis",
        title=f"Sumaria por {ctx.group_header.lower()} · {len(valued):,} partidas (100 %)",
        head=[ctx.group_header, "N.º partidas", "Importe", "% del total", "Ref. origen"],
    )
    flagged_groups = []
    for name, rows in ordered:
        subtotal = sum_amounts(rows)
        share = (subtotal / total) if total else Decimal(0)
        flag = "warn" if total and share > threshold else ""
        if flag:
            flagged_groups.append((name, share, rows, subtotal))
        main.add(
            [
                name,
                len(rows),
                ctx.fig_sum(rows, subtotal, label=f"Total {name}", extra={"group": name, "group_col": ctx.cols.group}),
                fmt_pct(share) if total else "n/a",
                ctx.ref_rows(rows),
            ],
            flag,
        )
    main.add(
        ["TOTAL", len(valued), ctx.fig_sum(valued, total, label="Total del auxiliar"), "100 %", f"{ctx.source_name} · {len(valued)} filas"],
        "total",
    )
    main.cap()
    main.flagged = bool(flagged_groups)
    if main.truncated:
        main.note = f"Se muestran los grupos de mayor importe; {main.truncated:,} grupos menores se omiten (el total los incluye)."

    out = AgentOutput(agent=AGENT, main=main)
    out.exceptions = len(flagged_groups)

    # -- estadísticas de la población
    n = len(valued)
    mean = total / n
    values = [float(r.amount) for r in valued]
    sd = math.sqrt(sum((v - float(mean)) ** 2 for v in values) / n)
    biggest = max(valued, key=lambda r: r.amount)
    smallest = min(valued, key=lambda r: r.amount)
    stats = Table(key="extra:estadisticas", title="Estadísticas de la población", head=["Medida", "Valor"])
    stats.add(["Partidas", n])
    stats.add(["Total", ctx.fig_sum(valued, total, label="Total del auxiliar")])
    stats.add(["Media", q2(mean)])
    stats.add(["Mínimo", ctx.fig_row(smallest, label="Mínimo")])
    stats.add(["Máximo", ctx.fig_row(biggest, label="Máximo")])
    stats.add(["Desviación estándar", q2(Decimal(sd))])
    out.extras.append(stats)

    # -- partidas mayores y cobertura acumulada
    top = sorted(valued, key=lambda r: r.amount, reverse=True)[:10]
    topt = Table(
        key="extra:top10",
        title="Partidas mayores (top 10) · cobertura para la muestra",
        head=[ctx.group_header, "Importe", "Cobertura acumulada", "Ref. origen"],
    )
    acc = Decimal(0)
    for row in top:
        acc += row.amount
        topt.add([row.group, ctx.fig_row(row), fmt_pct(acc / total) if total else "n/a", ctx.ref_rows([row])])
    out.extras.append(topt)
    top_coverage = (acc / total) if total else Decimal(0)

    # -- cuadre contra el mayor
    mayor = ctx.param_decimal("saldo_mayor", "NaN") if ctx.params.get("saldo_mayor") not in (None, "") else None
    diff = None
    if mayor is not None and mayor.is_finite():
        diff = q2(total - mayor)
        cuadre = Table(
            key="extra:cuadre",
            title="Cuadre auxiliar vs. mayor",
            head=["Concepto", "Importe"],
            flagged=diff != 0,
        )
        cuadre.add(["Total auxiliar", ctx.fig_sum(valued, total, label="Total del auxiliar")])
        cuadre.add(["Saldo según mayor", mayor])
        cuadre.add(["Diferencia: cuadra ✓" if diff == 0 else "Diferencia por investigar", diff], "error" if diff else "ok")
        out.extras.append(cuadre)
        if diff:
            out.exceptions += 1

    # -- corte alrededor del cierre
    cierre = ctx.param_date("fecha_cierre")
    dated = [r for r in valued if r.date]
    if cierre and dated:
        near = [r for r in dated if abs((r.date - cierre).days) <= CORTE_DIAS]
        corte = Table(
            key="extra:corte",
            title=f"Corte: partidas ±{CORTE_DIAS} días del cierre ({cierre.strftime('%d/%m/%Y')})",
            head=[ctx.group_header, "Documento", "Fecha", "Importe", "Posición", "Ref. origen"],
            flagged=bool(near),
        )
        for row in sorted(near, key=lambda r: r.date)[:200]:
            after = row.date > cierre
            corte.add(
                [row.group, row.doc_raw, row.date, ctx.fig_row(row), "Después del cierre" if after else "Antes del cierre", ctx.ref_rows([row])],
                "warn" if after else "",
            )
        if not near:
            corte.add(["Sin partidas cerca del cierre", "", "", "", "", ctx.source_name])
        out.extras.append(corte)
        out.exceptions += sum(1 for r in near if r.date > cierre)
    elif cierre and not dated:
        out.warnings.append("No se pudo hacer la prueba de corte: el auxiliar no tiene una columna de fecha reconocida.")

    # -- riesgos y hallazgos (NIA)
    if flagged_groups:
        names = ", ".join(g[0] for g in flagged_groups[:3])
        top_share = max(g[1] for g in flagged_groups)
        out.findings.append(
            finding(
                AGENT, "riesgo",
                f"Concentración del saldo en {len(flagged_groups)} grupo(s): {names}",
                "Concentra " + " y ".join(fmt_pct(g[1]) for g in flagged_groups[:3]) + " del total",
                ALTA if top_share > Decimal("0.5") else MEDIA,
                nia="NIA 315 · 330 · 530", aseveracion="Existencia · Valuación",
                importe=sum(g[3] for g in flagged_groups),
                origen=ctx.ref_rows(flagged_groups[0][2]),
                recomendacion="Probar al 100 % o confirmar los grupos concentrados (NIA 505); no muestrear a ciegas",
            )
        )
    if total and top_coverage >= Decimal("0.5"):
        out.findings.append(
            finding(
                AGENT, "riesgo", "Población dominada por partidas individualmente significativas",
                f"Las 10 mayores cubren {fmt_pct(top_coverage)} del total", MEDIA,
                nia="NIA 530", aseveracion="Existencia · Valuación",
                origen=ctx.ref_rows(top[:1]),
                recomendacion="Seleccionar esas partidas una por una y muestrear el resto (NIA 530)",
            )
        )
    if diff is None:
        out.findings.append(
            finding(
                AGENT, "riesgo", "Integridad del auxiliar no comprobada contra el mayor",
                "No se indicó el saldo según mayor", MEDIA,
                nia="NIA 500 · 330", aseveracion="Integridad", origen=ctx.source_name,
                recomendacion="Escribir el saldo del mayor y procesar de nuevo; si no cuadra, no usar el auxiliar como población",
            )
        )
    elif diff != 0:
        out.findings.append(
            finding(
                AGENT, "hallazgo", "Auxiliar vs. mayor",
                f"El total del auxiliar ({fmt_money(total)}) no cuadra con el saldo según mayor ({fmt_money(mayor)})",
                ALTA, importe=abs(diff), nia="NIA 500 · NIA 450", aseveracion="Integridad · Exactitud",
                condicion=f"Diferencia de {fmt_money(abs(diff))} entre el auxiliar y el mayor",
                criterio="NIA 500: fiabilidad de la información · NIA 450: acumular incorrecciones",
                causa="Por confirmar con la gerencia (partidas no registradas, cortes distintos o error de captura)",
                efecto=fmt_money(abs(diff)),
                recomendacion="Conciliar la diferencia partida por partida antes de usar el auxiliar como población",
                origen=f"{ctx.source_name} · total",
            )
        )
        out.findings.append(
            finding(
                AGENT, "riesgo", "Diferencia entre auxiliar y mayor: posible incorrección",
                f"Diferencia de {fmt_money(abs(diff))}", ALTA, importe=abs(diff),
                nia="NIA 315 · 450", aseveracion="Integridad · Exactitud", origen=f"{ctx.source_name} · total",
                recomendacion="Investigar y proponer ajuste si procede (NIA 450)",
            )
        )

    big = ", ".join(g[0] for g in flagged_groups)
    out.conclusion = (
        f"Se analizaron {n:,} partidas (100 %) por {fmt_money(total)}. "
        + (f"{big} concentra más del {fmt_pct(threshold, 0)} del total." if flagged_groups else f"Ningún grupo supera el {fmt_pct(threshold, 0)} del total.")
        + " El total debe cuadrar con el saldo del mayor."
    )
    return out
