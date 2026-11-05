"""Agente Revisión de contratos (NIA 500 · 501 · 250).

Prueba principal: clasificar cada contrato del registro según la fecha de cierre. Lee además
los contratos en PDF/Word (monto, vencimiento, cláusulas de riesgo) y los contrasta con el
gasto facturado.
"""
from __future__ import annotations

import re

from datetime import date, timedelta
from decimal import Decimal

from ..extract import clause_lines
from ..normalize import fmt_date, fmt_money, fmt_pct, q2
from ..shared import AgentOutput, Fig, Table
from .common import ALTA, BAJA, MEDIA, AgentContext, AgentError, finding, sum_amounts

AGENT = "contratos"

VENCIDO = "Vencido al cierre"
POR_VENCER = "Vence en 90 días"
VIGENTE = "Vigente"
SIN_FECHA = "Sin fecha de vencimiento"


def estado_vigencia(venc: date | None, cierre: date, ventana: int) -> str:
    if venc is None:
        return SIN_FECHA
    if venc < cierre:
        return VENCIDO
    if (venc - cierre).days <= ventana:
        return POR_VENCER
    return VIGENTE


_RX_EXPIRY = re.compile(r"venc|vigen|hasta|\bfin\b|t[eé]rmino|expira|caduc", re.I)


def run(ctx: AgentContext) -> AgentOutput:
    cierre = ctx.param_date("fecha_cierre")
    if cierre is None:
        raise AgentError("El agente de Contratos necesita la fecha de cierre.")
    ventana = int(ctx.param_float("ventana_dias", 90))
    date_header = ctx.headers[ctx.cols.date] if 0 <= ctx.cols.date < len(ctx.headers) else ""
    # Solo es un «registro de contratos» si la fecha del auxiliar es de vencimiento/vigencia. En un libro de
    # transacciones («Fecha» de pago o de factura) la vigencia sale de los contratos en PDF/Word, no de cada fila.
    expiry_column = bool(_RX_EXPIRY.search(date_header))
    has_register = expiry_column and any(r.date for r in ctx.rows)
    if not has_register and not ctx.contracts:
        raise AgentError(
            "El agente de Contratos necesita una columna con la fecha de vencimiento o contratos en PDF/Word."
        )

    rows = [r for r in ctx.rows if has_register]
    main = Table(
        key="analisis",
        title=f"Vigencia de contratos al cierre ({cierre.strftime('%d/%m/%Y')})",
        head=[ctx.group_header, "Importe", "Vence", "Estado", "Ref. origen"],
    )
    out = AgentOutput(agent=AGENT, main=main)
    classified = []
    for r in rows:
        state = estado_vigencia(r.date, cierre, ventana)
        classified.append((r, state))
    classified.sort(key=lambda t: (t[1] == VIGENTE, t[1]))
    counts = {s: 0 for s in (VENCIDO, POR_VENCER, VIGENTE, SIN_FECHA)}
    for r, state in classified:
        counts[state] += 1
        main.add(
            [r.group, ctx.fig_row(r) if r.amount is not None else "", r.date, state, ctx.ref_rows([r])],
            "" if state == VIGENTE else "warn",
        )
    main.flagged = any(c for s, c in counts.items() if s != VIGENTE)
    main.cap()
    out.exceptions = sum(c for s, c in counts.items() if s != VIGENTE)
    if not rows:
        reason = (f"El auxiliar es un registro de transacciones (columna «{date_header}»): la vigencia se toma de los contratos leídos"
                  if ctx.cols.date >= 0 and not expiry_column else "Sin registro de contratos con fecha de vencimiento")
        main.add([reason, "", "", "", ctx.source_name])

    # -- contratos leídos de PDF y Word
    contracts = ctx.contracts
    if contracts:
        leidos = Table(
            key="extra:contratos",
            title="Contratos leídos de PDF y Word",
            head=["Documento", "Pág.", "Monto", "Vence", "Estado al cierre"],
        )
        for c in contracts:
            ex = c.extraction
            monto = ex.get("Monto del contrato") if ex else None
            vence = ex.get("Vence") if ex else None
            state = "Sin fecha" if not vence else ("Vencido al cierre" if vence < cierre else "Vigente")
            leidos.add(
                [
                    c.doc,
                    c.page,
                    Fig(value=monto, doc=c.doc, page=c.page, bbox=c.bboxes.get("Monto del contrato"), label="Monto del contrato") if monto is not None else "",
                    vence,
                    state,
                ],
                "warn" if state != "Vigente" else "",
            )
        leidos.flagged = any(f for f in leidos.flags)
        out.extras.append(leidos)

        clauses = Table(
            key="extra:clausulas",
            title="Cláusulas de riesgo detectadas",
            head=["Documento", "Pág.", "Cláusula", "Texto"],
        )
        for c in contracts:
            for name, line in clause_lines(c.text):
                clauses.add([c.doc, c.page, name, line], "warn")
        clauses.flagged = bool(clauses.rows)
        if not clauses.rows:
            clauses.add(["Sin cláusulas de riesgo detectadas", "", "", ""])
        out.extras.append(clauses)
        out.exceptions += sum(1 for f in clauses.flags if f)

        # -- gasto facturado vs. contrato
        gasto = Table(
            key="extra:gasto",
            title="Gasto facturado vs. contrato",
            head=["Proveedor", "Monto contrato", "Facturado", "Uso del contrato", "Facturado después del vencimiento", "Origen"],
        )
        findings_gasto = []
        for c in contracts:
            ex = c.extraction
            monto = ex.get("Monto del contrato") if ex else None
            vence = ex.get("Vence") if ex else None
            text_lower = c.text.lower()
            for aux in ctx.aux_sets:
                if aux.cols.group < 0 or aux.cols.amount < 0:
                    continue
                names = sorted({r.group for r in aux.rows if len(r.group) > 3 and r.group.lower() in text_lower})
                for name in names:
                    rs = [r for r in aux.rows if r.group == name and r.amount is not None]
                    billed = sum_amounts(rs)
                    after = [r for r in rs if vence and r.date and r.date > vence]
                    after_sum = sum_amounts(after)
                    exceeds = monto is not None and billed > monto
                    if monto is None:
                        use = ""
                    elif exceeds:
                        use = f"⚠ Excede el contrato en {fmt_money(q2(billed - monto))}"
                    else:
                        use = f"Dentro del monto ({fmt_pct(billed / monto) if monto else 'n/a'})"
                    after_txt = f"{len(after)} facturas por {fmt_money(after_sum)} después del vencimiento" if after else "Ninguna"
                    gasto.add(
                        [
                            name,
                            Fig(value=monto, doc=c.doc, page=c.page, bbox=c.bboxes.get("Monto del contrato"), label="Monto del contrato") if monto is not None else "",
                            Fig(
                                value=billed, doc=aux.name, sheet=aux.sheet,
                                rows=[r.n for r in rs] if len(rs) <= 50 else [],
                                agg={"op": "sum", "amount_col": aux.cols.amount, "group_col": aux.cols.group, "group": name, "count": len(rs)} if len(rs) > 50 else None,
                                label=f"Facturado a {name}", col=aux.cols.amount,
                            ),
                            use,
                            after_txt,
                            f"{aux.name} + {c.doc}",
                        ],
                        "warn" if (exceeds or after) else "",
                    )
                    findings_gasto.append((name, monto, billed, exceeds, after, after_sum, aux, c, vence))
        if gasto.rows:
            gasto.flagged = any(gasto.flags)
            out.extras.append(gasto)
            out.exceptions += sum(1 for f in gasto.flags if f)
        # cada pago posterior al vencimiento, con su fila (para la integración y para revisarlo uno por uno)
        posteriores = Table(
            key="extra:posteriores", title="Pagos o facturas posteriores al vencimiento del contrato",
            head=["Indicador", "Proveedor", "Importe", "Detalle", "Ref. origen"], flagged=True,
        )
        for name, monto, billed, exceeds, after, after_sum, aux, c, vence in findings_gasto:
            for r in sorted(after, key=lambda r: r.date):
                posteriores.add(
                    ["Posterior al vencimiento del contrato", name,
                     Fig(value=r.amount, doc=aux.name, sheet=aux.sheet, rows=[r.n], label=f"Pago fila {r.n}", col=aux.cols.amount),
                     f"{fmt_date(r.date)}; el contrato venció el {fmt_date(vence)}", f"{aux.name} · fila {r.n} + {c.doc}"],
                    "warn",
                )
        if posteriores.rows:
            posteriores.cap()
            out.extras.append(posteriores)
        for name, monto, billed, exceeds, after, after_sum, aux, c, vence in findings_gasto:
            if exceeds:
                out.findings.append(
                    finding(AGENT, "hallazgo", f"Gasto por encima de lo contratado con {name}",
                            f"Se facturó {fmt_money(billed)} a {name} contra un contrato de {fmt_money(monto)}", ALTA,
                            importe=q2(billed - monto), nia="NIA 500 · 250 · 330", aseveracion="Ocurrencia · Exactitud",
                            condicion=f"Se facturó {fmt_money(billed)} a {name} contra un contrato de {fmt_money(monto)}",
                            criterio="NIA 500 · NIA 250 · NIA 330: pruebas sobre pagos fuera de contrato",
                            causa="Por confirmar con la gerencia (adenda no archivada, pagos fuera de contrato o sobreprecio)",
                            efecto=fmt_money(q2(billed - monto)),
                            recomendacion="Pedir adenda o autorización del exceso y revisar cada factura",
                            origen=f"{aux.name} + {c.doc}")
                )
            if after:
                out.findings.append(
                    finding(AGENT, "hallazgo", f"Facturas posteriores al vencimiento del contrato de {name}",
                            f"A {name}: {len(after)} facturas por {fmt_money(after_sum)} después del vencimiento ({fmt_date(vence)})",
                            MEDIA, importe=after_sum, nia="NIA 500 · 330", aseveracion="Ocurrencia",
                            condicion=f"{len(after)} facturas por {fmt_money(after_sum)} registradas después del {fmt_date(vence)}",
                            criterio="NIA 500 · NIA 330: gasto sin contrato vigente",
                            causa="Por confirmar con la gerencia (contrato vencido sin renovación)",
                            efecto=fmt_money(after_sum),
                            recomendacion="Pedir la renovación o aprobación del gasto",
                            origen=f"{aux.name} + {c.doc}")
                )
        if clauses.flagged:
            names = sorted({row[2] for row in clauses.rows})
            out.findings.append(
                finding(AGENT, "riesgo", "Pasivos contingentes por cláusulas: " + ", ".join(names[:4]),
                        f"{len(clauses.rows)} cláusulas detectadas en los contratos", MEDIA,
                        nia="NIA 501 · 250 · 450", aseveracion="Integridad · Presentación (revelación)",
                        origen=f"{clauses.rows[0][0]} · pág. {clauses.rows[0][1]}",
                        recomendacion="Confirmación de abogados y evaluación de provisión o revelación (NIA 501 · 450)")
            )
            out.findings.append(
                finding(AGENT, "hallazgo", f"Cláusulas de riesgo ({', '.join(names[:4])})",
                        f"{len(clauses.rows)} cláusulas de riesgo", MEDIA, nia="NIA 501 · 450",
                        condicion=f"{len(clauses.rows)} cláusulas de riesgo detectadas en los contratos",
                        criterio="NIA 501 · NIA 450: evaluar efectos en provisiones y revelaciones",
                        recomendacion="Revisar el texto de cada cláusula con la gerencia y evaluar la revelación",
                        origen=f"{clauses.rows[0][0]} · pág. {clauses.rows[0][1]}")
            )
    else:
        out.warnings.append("No se subieron contratos en PDF o Word: no se revisaron cláusulas, montos ni facturas posteriores al vencimiento.")

    # -- riesgos y hallazgos del registro
    vencidos = [r for r, s in classified if s == VENCIDO]
    por_vencer = [r for r, s in classified if s == POR_VENCER]
    sin_fecha = [r for r, s in classified if s == SIN_FECHA]
    if vencidos:
        total_v = sum_amounts(vencidos)
        out.findings.append(
            finding(AGENT, "hallazgo", "Contratos vencidos al cierre",
                    f"{len(vencidos)} contratos o saldos figuran vencidos al cierre ({fmt_date(cierre)}) por {fmt_money(total_v)}",
                    MEDIA, importe=total_v, nia="NIA 500 · 250", aseveracion="Ocurrencia · Derechos y obligaciones",
                    condicion=f"{len(vencidos)} contratos o saldos vencidos al {fmt_date(cierre)}",
                    criterio="NIA 500: el gasto debe tener un contrato vigente que lo respalde · NIA 250: cumplimiento",
                    causa="Por confirmar con la gerencia (renovación pendiente, contrato firmado sin registrar o servicio sin contrato)",
                    efecto=fmt_money(total_v),
                    recomendacion="Pedir el contrato vigente, la adenda o la autorización del gasto",
                    origen=ctx.ref_rows(vencidos))
        )
        out.findings.append(
            finding(AGENT, "riesgo", "Gasto sin contrato vigente: respaldo y cumplimiento",
                    f"{len(vencidos)} vencidos al cierre", ALTA if len(vencidos) / len(rows) > 0.5 else MEDIA,
                    nia="NIA 500 · 250", aseveracion="Ocurrencia · Derechos y obligaciones", origen=ctx.ref_rows(vencidos),
                    recomendacion="Solicitar el contrato o adenda y evaluar si el gasto tiene respaldo (NIA 500)")
        )
    if por_vencer:
        out.findings.append(
            finding(AGENT, "riesgo", "Renovaciones próximas: compromisos a revelar",
                    f"{len(por_vencer)} vencen en los {ventana} días siguientes al cierre", BAJA, nia="NIA 315",
                    aseveracion="Presentación · Revelación", origen=ctx.ref_rows(por_vencer),
                    recomendacion="Preguntar a la gerencia por renovaciones y compromisos futuros")
        )
    if sin_fecha:
        out.findings.append(
            finding(AGENT, "hallazgo", "Registros sin fecha de vencimiento",
                    f"{len(sin_fecha)} registros sin fecha de vencimiento", BAJA, nia="NIA 500 · 315",
                    condicion=f"{len(sin_fecha)} registros sin fecha de vencimiento",
                    criterio="NIA 500: evidencia insuficiente · NIA 315: control del archivo contractual",
                    causa="Por confirmar con la gerencia (contrato indefinido o dato no capturado)",
                    recomendacion="Completar la fecha o pedir el contrato", origen=ctx.ref_rows(sin_fecha))
        )

    out.conclusion = (
        f"{counts[VENCIDO]} contratos vencidos al cierre, {counts[POR_VENCER]} vencen en {ventana} días y "
        f"{counts[SIN_FECHA]} sin fecha. Verificar si siguen generando gastos sin contrato vigente."
    )
    return out
