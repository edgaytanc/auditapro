"""Agente Predictivo (NIA 520 · 315).

Prueba principal: serie mensual con tendencia lineal (mínimos cuadrados), desviación de cada
mes contra la tendencia y proyección. La tendencia usa el mes calendario como eje X, de modo
que un mes sin movimientos no comprime el tiempo.
"""
from __future__ import annotations

from decimal import Decimal

from ..normalize import fmt_money, fmt_pct, q2
from ..shared import AgentOutput, Fig, Table
from .common import ALTA, BAJA, MEDIA, AgentContext, AgentError, finding, sum_amounts

AGENT = "predictivo"


def _label(ym: tuple[int, int]) -> str:
    return f"{ym[0]}-{ym[1]:02d}"


def _month_index(ym: tuple[int, int]) -> int:
    return ym[0] * 12 + (ym[1] - 1)


def _from_index(idx: int) -> tuple[int, int]:
    return idx // 12, idx % 12 + 1


def run(ctx: AgentContext) -> AgentOutput:
    if ctx.cols.date < 0:
        raise AgentError("El agente Predictivo necesita una columna de fecha.")
    rows = [r for r in ctx.rows if r.amount is not None and r.date]
    if not rows:
        raise AgentError("No hay filas con fecha e importe reconocibles para armar la serie mensual.")
    rango = Decimal(str(ctx.param_float("rango", 30.0))) / 100
    meses = int(ctx.param_float("meses_proyectar", 3))

    months: dict[tuple[int, int], list] = {}
    for r in rows:
        months.setdefault((r.date.year, r.date.month), []).append(r)
    keys = sorted(months)
    totals = {k: sum_amounts(months[k]) for k in keys}
    base = _month_index(keys[0])
    xs = [_month_index(k) - base for k in keys]
    ys = [float(totals[k]) for k in keys]
    n = len(keys)
    mean_y = sum(ys) / n
    mean_x = sum(xs) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    intercept = mean_y - slope * mean_x

    main = Table(
        key="analisis",
        title=f"Serie mensual y tendencia · {n} meses",
        head=["Mes", "Total", "Tendencia", "Desviación", "Ref. origen"],
    )
    out = AgentOutput(agent=AGENT, main=main)
    out_of_range = []
    for k, x, y in zip(keys, xs, ys):
        trend = intercept + slope * x
        dev = (Decimal(str(y)) - Decimal(str(trend))) / Decimal(str(trend)) if trend else None
        flag = "warn" if dev is not None and abs(dev) > rango else ""
        if flag:
            out_of_range.append((k, totals[k], q2(Decimal(str(trend))), dev, months[k]))
        main.add(
            [
                _label(k),
                ctx.fig_sum(months[k], totals[k], label=f"Total {_label(k)}", extra={"month": _label(k), "date_col": ctx.cols.date}),
                q2(Decimal(str(trend))),
                fmt_pct(dev) if dev is not None else "n/a",
                ctx.ref_rows(months[k]),
            ],
            flag,
        )
    for j in range(1, meses + 1):
        main.add(
            [f"Proyección +{j}", q2(Decimal(str(intercept + slope * (xs[-1] + j)))), "", "", f"Tendencia lineal sobre {n} meses"],
            "total",
        )
    main.flagged = bool(out_of_range)
    out.exceptions = len(out_of_range)
    if n < 6:
        out.warnings.append(f"La serie tiene solo {n} mes(es): la tendencia y la proyección son referenciales.")

    # -- estacionalidad y cierre
    avg = sum(totals.values()) / n
    peak = max(keys, key=lambda k: totals[k])
    valley = min(keys, key=lambda k: totals[k])
    last3 = keys[-3:]
    last3_avg = sum(totals[k] for k in last3) / len(last3)
    seasonal_warn = avg > 0 and last3_avg > avg * Decimal("1.2")
    seas = Table(
        key="extra:estacionalidad",
        title="Estacionalidad y cierre",
        head=["Indicador", "Mes", "Importe", "Lectura"],
        flagged=seasonal_warn,
    )
    seas.add(["Mes pico", _label(peak), totals[peak], f"{fmt_pct(totals[peak] / avg - 1)} sobre el promedio" if avg else ""])
    seas.add(["Mes valle", _label(valley), totals[valley], f"{fmt_pct(totals[valley] / avg - 1)} vs. promedio" if avg else ""])
    seas.add(
        [
            "Último trimestre (promedio)",
            ", ".join(_label(k) for k in last3),
            q2(last3_avg),
            "⚠ más de 20 % sobre el promedio: revisar registros al cierre" if seasonal_warn else "Dentro de lo normal",
        ],
        "warn" if seasonal_warn else "",
    )
    out.extras.append(seas)
    if seasonal_warn:
        out.exceptions += 1

    # -- variación por grupo entre semestres (último ejercicio con datos)
    last_year = keys[-1][0]
    by_group: dict[str, list[Decimal]] = {}
    for r in rows:
        if r.date.year != last_year:
            continue
        slot = by_group.setdefault(r.group or "(sin dato)", [Decimal(0), Decimal(0)])
        slot[0 if r.date.month <= 6 else 1] += r.amount
    changes = sorted(by_group.items(), key=lambda kv: abs(kv[1][1] - kv[1][0]), reverse=True)[:8]
    sem = Table(
        key="extra:semestres",
        title=f"Variación por grupo · 1.er vs. 2.º semestre de {last_year}",
        head=[ctx.group_header, "1.er semestre", "2.º semestre", "Variación"],
    )
    new_groups = []
    for name, (s1, s2) in changes:
        variation = fmt_pct(s2 / s1 - 1) if s1 else "nuevo"
        if not s1 or (s1 and abs(s2 / s1 - 1) > 1):
            new_groups.append(name)
        sem.add([name, q2(s1), q2(s2), variation])
    out.extras.append(sem)

    # -- análisis horizontal con 2 o más ejercicios
    years = sorted({k[0] for k in keys})
    if len(years) >= 2:
        yearly = {y: sum_amounts([r for r in rows if r.date.year == y]) for y in years}
        hor = Table(key="extra:horizontal", title="Análisis horizontal por ejercicio", head=["Ejercicio", "Total", "Variación vs. anterior"])
        prev = None
        for y in years:
            hor.add([str(y), yearly[y], (fmt_pct(yearly[y] / prev - 1) if prev else "—")])
            prev = yearly[y] or None
        out.extras.append(hor)

    # -- riesgos y hallazgos
    for k, real, trend, dev, month_rows in out_of_range[:6]:
        out.findings.append(
            finding(
                AGENT, "hallazgo", f"Fluctuación fuera de ±{fmt_pct(rango, 0)} en {_label(k)}",
                f"En {_label(k)} el total fue {fmt_money(real)} contra {fmt_money(trend)} esperado por la tendencia ({fmt_pct(dev)})",
                ALTA if abs(dev) > Decimal("0.6") else MEDIA,
                importe=abs(real - trend), nia="NIA 520 · 330", aseveracion="Ocurrencia · Corte",
                condicion=f"{_label(k)}: {fmt_money(real)} vs. {fmt_money(trend)} esperado ({fmt_pct(dev)})",
                criterio=f"NIA 520: investigar las fluctuaciones que difieren de lo esperado (umbral ±{fmt_pct(rango, 0)}, parámetro del agente)",
                causa="Por confirmar con la gerencia (estacionalidad, hecho no recurrente o error)",
                efecto=fmt_money(abs(real - trend)),
                recomendacion="Pedir explicación a la gerencia y corroborarla con evidencia; ampliar pruebas si no se sustenta (NIA 520 · 330)",
                origen=ctx.ref_rows(month_rows),
            )
        )
    if out_of_range:
        out.findings.append(
            finding(
                AGENT, "riesgo", f"Fluctuaciones sin explicar en {len(out_of_range)} mes(es)",
                ", ".join(_label(o[0]) for o in out_of_range[:4]) + f" fuera de ±{fmt_pct(rango, 0)} de la tendencia",
                ALTA if len(out_of_range) >= 3 else MEDIA,
                nia="NIA 315 · 520", aseveracion="Ocurrencia · Corte", origen=ctx.ref_rows(out_of_range[0][4]),
                recomendacion="Obtener explicación y evidencia de la gerencia (NIA 520)",
            )
        )
    if seasonal_warn:
        out.findings.append(
            finding(
                AGENT, "hallazgo", "Último trimestre sobre el promedio del año",
                f"El promedio del último trimestre ({fmt_money(q2(last3_avg))}) supera en más de 20 % el promedio del año",
                MEDIA, importe=q2(last3_avg), nia="NIA 330 · 240", aseveracion="Corte · Ocurrencia",
                condicion="Concentración de registros en los últimos meses del ejercicio",
                criterio="NIA 330: pruebas de corte · NIA 240: manipulación de resultados",
                causa="Por confirmar con la gerencia (cierres anticipados, ajustes de fin de año o registros fuera de período)",
                efecto=fmt_money(q2(last3_avg)),
                recomendacion="Probar el corte de los registros de los últimos meses",
                origen=f"{ctx.source_name} · últimos 3 meses",
            )
        )
        out.findings.append(
            finding(
                AGENT, "riesgo", "Registros concentrados al cierre: corte de operaciones",
                "Último trimestre sobre el promedio del año", MEDIA, nia="NIA 330 · 240", aseveracion="Corte · Ocurrencia",
                origen=ctx.source_name,
                recomendacion="Pruebas de corte sobre documentos de diciembre y enero (NIA 330)",
            )
        )
    if new_groups:
        out.findings.append(
            finding(
                AGENT, "riesgo", f"Cambios fuertes entre semestres en {len(new_groups)} grupo(s): " + ", ".join(new_groups[:3]),
                "Variación de más de 100 % o grupo nuevo en el 2.º semestre", BAJA,
                nia="NIA 315", aseveracion="Ocurrencia · Clasificación", origen=ctx.source_name,
                recomendacion="Preguntar por cambios del negocio, precios o proveedores nuevos",
            )
        )

    direction = "creciente" if slope >= 0 else "decreciente"
    out.conclusion = (
        f"{n} meses analizados. Tendencia {direction} de {fmt_money(q2(Decimal(str(abs(slope)))))} por mes. "
        + (
            f"Meses fuera de rango (±{fmt_pct(rango, 0)}): {', '.join(_label(o[0]) for o in out_of_range)}. Requieren explicación de la gerencia (NIA 520)."
            if out_of_range
            else f"Ningún mes se desvía más de {fmt_pct(rango, 0)} de la tendencia."
        )
    )
    return out
