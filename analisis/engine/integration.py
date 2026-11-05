"""Integración del auxiliar para los papeles que traen su propia tabla de detalle.

Ejemplo: «10_INTEGRACION_EGRESOS» (Financiera · Pruebas sustantivas · Caja y bancos) tiene la tabla
«DETALLE DE EGRESOS DEL PERÍODO» (No., Tipo doc., Fecha, Descripción, Monto, Cta. contable, Marca,
Observaciones) con un TOTAL ``=SUM(...)``. Aquí se arma, con el 100 % del auxiliar:

- ``integracion``: una fila por partida, con su origen, la marca y las observaciones de los agentes;
- ``integracion_mes``: el resumen mensual (para cuando el papel tiene menos filas que partidas).

Las cifras las calcula el código (``Decimal``) y cada una lleva su origen (fila o suma mensual verificable).
"""
from __future__ import annotations

import calendar
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from .agents.common import AgentContext, ColumnMap
from .crossmatch import AuxRow, CruceRow
from .shared import Fig, Table

MAX_DETAIL_ROWS = 5000
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]

_RX_TIPO = re.compile(r"^tipo", re.I)
_RX_DESC = re.compile(r"concepto|descrip|detalle|glosa", re.I)
_RX_CUENTA = re.compile(r"\bcta\b|cuenta", re.I)


def _col(headers: list[str], rx: re.Pattern, exclude: set[int]) -> int:
    for i, h in enumerate(headers):
        if i not in exclude and rx.search(str(h or "")):
            return i
    return -1


def _text(values: list, i: int) -> str:
    if i < 0 or i >= len(values) or values[i] is None:
        return ""
    v = values[i]
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _short(label: str) -> str:
    label = re.sub(r"\s+", " ", str(label)).strip()
    return label if len(label) <= 60 else label[:58] + "…"


def row_alerts(tables: list[Table], source_name: str, cruce: list[CruceRow]) -> tuple[dict[int, list[str]], set[int]]:
    """Observaciones por fila del auxiliar (de las tablas de los agentes y del cruce) y filas cotejadas."""
    alerts: dict[int, list[str]] = defaultdict(list)
    verified: set[int] = set()
    for t in tables:
        flags = t.flags or [""] * len(t.rows)
        indicator = bool(t.head) and str(t.head[0]).strip().lower() == "indicador"
        for row, flag in zip(t.rows, flags):
            if flag not in ("warn", "error"):
                continue
            figs = [c for c in row if isinstance(c, Fig) and c.doc == source_name and len(c.rows) == 1 and c.page is None]
            if not figs:
                continue
            label = _short(row[0] if indicator else t.title.split("·")[-1])
            detail = _short(row[3]) if indicator and len(row) > 3 and row[3] not in (None, "") else ""
            text = f"{label} ({detail})" if detail else label
            for f in figs:
                if text not in alerts[f.rows[0]]:
                    alerts[f.rows[0]].append(text)
    for c in cruce:
        if c.aux_row is None:
            continue
        ref = f"{c.doc_name} pág. {c.page}"
        if c.estado == "cuadra":
            verified.add(c.aux_row)
            alerts[c.aux_row].append(f"Cotejado con documento {c.numero} ({ref})")
        else:
            alerts[c.aux_row].append(f"Documento {c.numero}: {c.motivo[:1].lower()}{c.motivo[1:]} ({ref})")
    return alerts, verified


def build(source_name: str, sheet: str, headers: list[str], cols: ColumnMap, rows: list[AuxRow],
          agent_tables: list[Table], cruce: list[CruceRow]) -> list[Table]:
    if cols.amount < 0 or not rows:
        return []
    ctx = AgentContext(source_name=source_name, sheet=sheet, headers=headers, cols=cols, rows=rows)
    used = {cols.amount, cols.date, cols.doc, cols.group}
    i_tipo = _col(headers, _RX_TIPO, used)
    i_desc = _col(headers, _RX_DESC, used | {i_tipo})
    i_cta = _col(headers, _RX_CUENTA, used | {i_tipo, i_desc}) if not _RX_CUENTA.search(str(headers[cols.group] if 0 <= cols.group < len(headers) else "")) else cols.group
    alerts, verified = row_alerts(agent_tables, source_name, cruce)

    valued = [r for r in rows if r.amount is not None]
    valued.sort(key=lambda r: (r.date is None, r.date or 0, r.n))

    detail = Table(
        key="integracion", title="Integración del auxiliar (para la tabla de detalle del papel)",
        head=["Fila", "Fecha", "Tipo doc.", "No. documento", "Proveedor / beneficiario", "Descripción", "Cuenta", "Monto",
              "Marca", "Observaciones"],
    )
    for r in valued[:MAX_DETAIL_ROWS]:
        obs = sorted(alerts.get(r.n, []), key=lambda o: o.startswith("Cotejado"))
        detail.add(
            [r.n, r.date, _text(r.values, i_tipo), r.doc_raw, r.group, _text(r.values, i_desc), _text(r.values, i_cta),
             ctx.fig_row(r, label=f"Partida fila {r.n}"), "✓" if r.n in verified else "", "; ".join(obs)],
            "warn" if any(not o.startswith("Cotejado") for o in obs) else ("ok" if r.n in verified else ""),
        )
    if len(valued) > MAX_DETAIL_ROWS:
        detail.truncated = len(valued) - MAX_DETAIL_ROWS
        detail.note = f"Se guardan las primeras {MAX_DETAIL_ROWS:,} partidas; los totales mensuales incluyen las {len(valued):,}."

    by_month: dict[str, list[AuxRow]] = defaultdict(list)
    for r in valued:
        by_month[f"{r.date.year}-{r.date.month:02d}" if r.date else "sin-fecha"].append(r)
    monthly = Table(
        key="integracion_mes", title="Integración mensual del auxiliar",
        head=["Mes", "Etiqueta", "Partidas", "Tipo doc.", "Cuentas", "Monto", "Con alerta", "Cotejadas", "Último día"],
    )
    for key in sorted(by_month, key=lambda k: (k == "sin-fecha", k)):
        items = by_month[key]
        total = sum((r.amount for r in items), Decimal(0))
        if key == "sin-fecha":
            label, last = "Sin fecha", None
            fig = ctx.fig_sum(items, total, label="Partidas sin fecha")
        else:
            y, m = int(key[:4]), int(key[5:])
            label = f"{MESES[m - 1].capitalize()} {y}"
            last = date(y, m, calendar.monthrange(y, m)[1])  # integración mensual: al cierre de cada mes
            fig = ctx.fig_sum(items, total, label=f"Total {label}", extra={"month": key, "date_col": cols.date})
        tipos = Counter(_text(r.values, i_tipo) for r in items if _text(r.values, i_tipo))
        cuentas = sorted({_text(r.values, i_cta) for r in items if _text(r.values, i_cta)})
        with_alert = sum(1 for r in items if any(not o.startswith("Cotejado") for o in alerts.get(r.n, [])))
        monthly.add(
            [key, label, len(items), (tipos.most_common(1)[0][0] if len(tipos) == 1 else ("Varios" if tipos else "")),
             (cuentas[0] if len(cuentas) == 1 else ("Varias" if cuentas else "")), fig, with_alert,
             sum(1 for r in items if r.n in verified), last],
            "warn" if with_alert else "",
        )
    # columnas originales de cada fila: con ellas se pega cada transacción en la columna del papel que tiene su nombre
    fuente = Table(key="integracion_fuente", title=f"Columnas originales · {source_name}", head=["Fila"] + [str(h) for h in headers])
    for r in valued[:MAX_DETAIL_ROWS]:
        fuente.add([r.n] + [_cell(v) for v in r.values])
    return [detail, monthly, fuente]


def _cell(v):
    """Valor guardable en JSON (los Decimal y fechas los maneja ``table_to_dict``)."""
    if v is None or isinstance(v, (str, int, float, Decimal, date)):
        return v
    return str(v)
