"""Ejecución de una corrida: etapas 01→04, consolidación y guardado.

Cada etapa actualiza el avance y comprueba si el auditor detuvo la corrida. Los números
salen del motor determinístico (``engine/``); la IA solo interviene si está configurada y
siempre con su resultado validado.
"""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .engine import consolidate
from .engine.agents import RUNNERS, AgentContext, AgentError, build_aux_rows, resolve_columns
from .engine.agents.common import AGENTES, AuxSet, ColumnMap, DocSection
from .engine.ai import ClaudeClient
from .engine import structured_fill
from .engine.classify import (
    TIPO_AUXILIAR,
    TIPO_COMPROBANTE,
    TIPO_CONTRATO,
    TIPO_FACTURA,
    TIPO_OTRO,
    TIPO_SIN_TEXTO,
    TIPOS_CRUZABLES,
    Classification,
    classify_text,
)
from .engine.crossmatch import AuxIndex, CruceRow, match_document
from .engine.extract import Extraction, amount_of, date_of, extract_fields
from .engine.normalize import fmt_money, fmt_num, parse_amount, parse_date
from .engine import integration
from .engine.orchestrator import build_plan
from .engine.readers import Limits, SourceDoc, find_pdf_bboxes, read_document
from .engine.shared import Fig, Finding, Table, table_to_dict
from .engine.template_fill import inspect_template
from .models import (
    BitacoraAnalisis,
    CifraAnalisis,
    CorridaAnalisis,
    DocumentoAnalisis,
    HallazgoAnalisis,
)

logger = logging.getLogger(__name__)

PDF_FIELDS = ("Número", "Total", "Saldo final", "Monto del contrato", "Vence")
AI_TIPOS = ["Factura", "Estado de cuenta", "Contrato", "Planilla / nómina", "Comprobante de pago"]


class Stopped(Exception):
    """El auditor detuvo la corrida."""


class RunFailed(Exception):
    """La corrida no puede continuar; el mensaje se muestra al auditor."""


def _limits() -> Limits:
    return Limits(max_rows=settings.ANALISIS_MAX_ROWS, max_pdf_pages=settings.ANALISIS_MAX_PDF_PAGES)


class _Control:
    def __init__(self, run: CorridaAnalisis):
        self.run = run

    def stage(self, label: str, progress: int) -> None:
        current = CorridaAnalisis.objects.only("estado").get(pk=self.run.pk).estado
        if current == CorridaAnalisis.Estado.DETENIDO:
            raise Stopped()
        self.run.touch(etapa=label, progreso=progress)


# --------------------------------------------------------------------------- etapa 01

def _read_all(run: CorridaAnalisis, ctl: _Control) -> dict[int, SourceDoc]:
    docs: dict[int, SourceDoc] = {}
    items = list(run.documentos.exclude(rol=DocumentoAnalisis.Rol.PLANTILLA))
    for i, d in enumerate(items, start=1):
        ctl.stage(f"01 · Leyendo {d.nombre_original}", 5 + int(20 * i / max(len(items), 1)))
        src = read_document(d.archivo.path, d.nombre_original, _limits())
        docs[d.pk] = src
        d.paginas_leidas = len(src.pages)
        d.filas_leidas = sum(len(t.rows) for t in src.tabular)
        d.estado_lectura = "error" if src.error else ("sin_texto" if src.pages and all(p.method == "sin_texto" for p in src.pages) else "ok")
        d.nota = " ".join([src.error] + src.warnings).strip()
        d.save(update_fields=["paginas_leidas", "filas_leidas", "estado_lectura", "nota"])
    return docs


def _classify(docs_db: dict[int, DocumentoAnalisis], docs: dict[int, SourceDoc], ai: ClaudeClient) -> tuple[list[DocSection], Table]:
    table = Table(key="clasificacion", title="Clasificación por página", head=["Documento", "Página", "Tipo", "Formato", "Método", "Confianza"])
    sections: list[DocSection] = []
    for pk, src in docs.items():
        if src.error:
            table.add([src.name, "—", "No se pudo leer", src.kind, "—", ""], "error")
            continue
        if src.tabular:
            for tab in src.tabular:
                table.add([f"{src.name} · {tab.sheet}", "—", TIPO_AUXILIAR, src.kind, "regla", ""])
        for page in src.pages:
            if page.method == "sin_texto":
                table.add([src.name, page.number, TIPO_SIN_TEXTO, src.kind, "—", ""], "warn")
                continue
            cls = classify_text(page.text)
            if cls.tipo == TIPO_OTRO and ai.enabled and len(page.text) >= 40:
                suggestion = ai.classify_page(page.text, AI_TIPOS)
                if suggestion and suggestion.confianza >= 0.6 and suggestion.tipo != TIPO_OTRO:
                    cls = suggestion
            sections.append(
                DocSection(doc=src.name, page=page.number, tipo=cls.tipo, confianza=cls.confianza, metodo=cls.metodo,
                           text=page.text, path=src.path)
            )
            table.add([src.name, page.number, cls.tipo, src.kind, cls.metodo, f"{cls.confianza:.0%}" if cls.confianza else ""])
    return sections, table


# --------------------------------------------------------------------------- etapa 02

_AI_FIELDS = {
    "Factura": ["Número", "Fecha", "NIT", "Proveedor", "Total"],
    "Comprobante de pago": ["Número", "Fecha", "Beneficiario", "Total"],
    "Contrato": ["Partes", "Objeto", "Monto del contrato", "Vence"],
}


def _ai_fill(section: DocSection, ex: Extraction, ai: ClaudeClient) -> None:
    wanted = _AI_FIELDS.get(section.tipo)
    if not wanted or not ai.enabled:
        return
    missing = [f for f in wanted if f not in ex.fields]
    needs = {
        "Factura": {"Número", "Total"}, "Comprobante de pago": {"Número", "Total"}, "Contrato": {"Monto del contrato", "Vence"},
    }[section.tipo]
    if not (needs & set(missing)):
        return
    got = ai.extract_fields(section.text, section.tipo, missing)
    for name, raw in (got or {}).items():
        if name in ("Total", "Monto del contrato"):
            value = parse_amount(raw)
        elif name in ("Fecha", "Vence"):
            value = parse_date(raw)
        else:
            value = raw
        if value not in (None, ""):
            ex.put(name, value, raw, method="IA")


def _extract(sections: list[DocSection], ai: ClaudeClient) -> Table:
    table = Table(key="extraccion", title="Datos extraídos", head=["Documento", "Pág.", "Tipo", "Campo", "Valor", "Método"])
    by_pdf: dict[str, list[tuple[DocSection, str, str]]] = {}
    for s in sections:
        if s.tipo == TIPO_OTRO:
            continue
        ex = extract_fields(s.text, s.tipo)
        _ai_fill(s, ex, ai)
        s.extraction = ex
        for name, f in ex.fields.items():
            table.add([s.doc, s.page, s.tipo, name, f.value, f.method])
            if name in PDF_FIELDS and s.path.lower().endswith(".pdf") and f.raw:
                by_pdf.setdefault(s.path, []).append((s, name, f.raw))
    for path, items in by_pdf.items():
        boxes = find_pdf_bboxes(path, [(s.page, raw) for s, _, raw in items])
        for s, name, raw in items:
            box = boxes.get((s.page, raw))
            if box:
                s.bboxes[name] = box
    return table


# --------------------------------------------------------------------------- etapa 03

def _pick_aux(run: CorridaAnalisis, docs_db: dict[int, DocumentoAnalisis], docs: dict[int, SourceDoc], template_table=None):
    candidates = [(pk, d) for pk, d in docs.items() if d.tabular]
    if not candidates:
        return None
    wanted_id = run.parametros.get("auxiliar_id")
    if wanted_id:
        for pk, d in candidates:
            if str(pk) == str(wanted_id):
                return pk, d
    preferred = [(pk, d) for pk, d in candidates if docs_db[pk].rol == DocumentoAnalisis.Rol.AUXILIAR] or candidates
    if template_table is not None and len(preferred) > 1:
        # el archivo cuyas columnas tienen los nombres de la tabla del papel (p. ej. el auxiliar de facturas y no el mayor)
        return max(preferred, key=lambda t: (structured_fill.match_score(template_table, [str(h) for h in t[1].main_table.headers]),
                                             len(t[1].main_table.rows)))
    return max(preferred, key=lambda t: len(t[1].main_table.rows))


def _tab_of(src: SourceDoc, sheet: str | None):
    if sheet:
        for t in src.tabular:
            if t.sheet == sheet:
                return t
    return src.main_table


def _cruce(sections: list[DocSection], index: AuxIndex | None, tolerance: Decimal) -> list[CruceRow]:
    rows: list[CruceRow] = []
    if index is None:
        return rows
    for s in sections:
        ex = s.extraction
        if not ex or s.tipo not in TIPOS_CRUZABLES:
            continue
        numero = ex.get("Número")
        total = amount_of(ex)
        if not numero and total is None:
            continue
        estado, motivo, aux = match_document(index, numero or "", total, date_of(ex), tolerance, proveedor=str(ex.get("Proveedor") or ""))
        fig = Fig(value=total, doc=s.doc, page=s.page, bbox=s.bboxes.get("Total"), label=f"Importe documento {numero or ''}".strip()) if total is not None else None
        rows.append(
            CruceRow(
                numero=str(numero or ""), proveedor=str(ex.get("Proveedor") or ""), total=total, estado=estado, motivo=motivo,
                doc_name=s.doc, page=s.page, aux_row=aux.n if aux else None, aux_amount=aux.amount if aux else None, fig=fig,
            )
        )
    return rows


# --------------------------------------------------------------------------- orquestación

def _context_text(run, docs: dict[int, SourceDoc], template_text: str, aux_headers: list[str]) -> str:
    names = " ".join(d.name for d in docs.values())
    return " ".join([run.titulo, template_text, names, " ".join(aux_headers)])


def _walk_figs(tables: list[Table]):
    for t in tables:
        for row in t.rows:
            for cell in row:
                if isinstance(cell, Fig):
                    yield cell


def execute_run(run_id: int) -> None:
    run = CorridaAnalisis.objects.select_related("audit").get(pk=run_id)
    if run.estado != CorridaAnalisis.Estado.EN_COLA:
        return
    run.estado = CorridaAnalisis.Estado.EJECUTANDO
    run.iniciado_en = timezone.now()
    run.save(update_fields=["estado", "iniciado_en"])
    BitacoraAnalisis.registrar(run, run.creado_por, "inicio", {"agentes_solicitados": run.agentes_solicitados})
    ctl = _Control(run)
    try:
        _execute(run, ctl)
    except Stopped:
        run.estado = CorridaAnalisis.Estado.DETENIDO
        run.terminado_en = timezone.now()
        run.save(update_fields=["estado", "terminado_en"])
        BitacoraAnalisis.registrar(run, run.creado_por, "detenida", {})
    except RunFailed as exc:
        _fail(run, str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Audita Análisis: falló la corrida %s", run_id)
        _fail(run, "Ocurrió un error inesperado al procesar los archivos. Revise que no estén dañados e intente de nuevo.")


def _fail(run: CorridaAnalisis, message: str) -> None:
    run.estado = CorridaAnalisis.Estado.ERROR
    run.error_mensaje = message
    run.terminado_en = timezone.now()
    run.save(update_fields=["estado", "error_mensaje", "terminado_en"])
    BitacoraAnalisis.registrar(run, run.creado_por, "error", {"mensaje": message})


def _execute(run: CorridaAnalisis, ctl: _Control) -> None:
    ai = ClaudeClient.from_settings()
    warnings: list[str] = []
    docs_db = {d.pk: d for d in run.documentos.exclude(rol=DocumentoAnalisis.Rol.PLANTILLA)}
    template_doc = run.plantilla

    # -- plantilla (solo lectura)
    template_text, template_info = "", None
    if template_doc:
        try:
            template_info = inspect_template(template_doc.archivo.path)
            template_text = template_info.text_sample
            warnings += [f"El papel de trabajo {r}." for r in template_info.risks]
        except Exception:  # noqa: BLE001
            raise RunFailed("No se pudo abrir el papel de trabajo. Verifique que sea un Excel (.xlsx) válido y sin contraseña.") from None

    # -- 01 lectura y clasificación
    docs = _read_all(run, ctl)
    for pk, d in docs.items():
        if d.error:
            warnings.append(f"{d.name}: {d.error}")
        warnings += [f"{d.name}: {w}" for w in d.warnings]
    ctl.stage("01 · Clasificando páginas", 28)
    sections, classification = _classify(docs_db, docs, ai)

    # -- 02 extracción
    ctl.stage("02 · Extrayendo datos de los documentos", 40)
    extraction = _extract(sections, ai)

    # -- auxiliar y columnas
    picked = _pick_aux(run, docs_db, docs, structured_fill.template_table(template_doc.archivo.path) if template_doc else None)
    aux_ctx = None
    index = None
    if picked:
        pk, src = picked
        tab = _tab_of(src, run.parametros.get("hoja"))
        cols = resolve_columns(tab.headers, run.columnas, "masivo")
        rows = build_aux_rows(tab, cols)
        index = AuxIndex(rows)
        aux_ctx = (src, tab, cols, rows)
    else:
        warnings.append("No se subió un auxiliar en Excel o CSV: no hay cruce ni análisis de datos; solo se clasificaron y extrajeron los documentos.")

    # -- 03 cruce
    ctl.stage("03 · Cruzando documentos contra el auxiliar", 52)
    tolerance = Decimal(str(run.parametros.get("tolerancia", "0.5"))) / 100
    cruce = _cruce(sections, index, tolerance)

    # -- plan del orquestador
    ctl.stage("04 · Orquestador: planificando", 58)
    has_dates = bool(aux_ctx and aux_ctx[2].date >= 0 and any(r.date for r in aux_ctx[3]))
    has_amounts = bool(aux_ctx and any(r.amount is not None for r in aux_ctx[3]))
    contract_docs = sum(1 for s in sections if s.tipo == TIPO_CONTRATO)
    requested = list(run.agentes_solicitados or [])
    requested_source = "auditor"
    if not requested and run.instruccion and ai.enabled:
        suggested = ai.interpret_request(run.instruccion, list(AGENTES))
        if suggested:
            requested = [a for a in suggested if a in AGENTES]
            requested_source = "ia"
    plan = build_plan(
        context_text=_context_text(run, docs, template_text, aux_ctx[1].headers if aux_ctx else []),
        request=run.instruccion, requested_agents=requested or None, requested_source=requested_source,
        has_tabular=bool(aux_ctx), has_dates=has_dates, has_amounts=has_amounts, contract_docs=contract_docs,
    )

    # -- 04 agentes
    params = dict(run.parametros)
    params.setdefault("fecha_cierre", run.audit.fechaEnd.date().isoformat() if run.audit.fechaEnd else None)
    params["tipo_papel"] = plan.kind_code  # p. ej. «ingresos»: facturas emitidas por la entidad, no de un proveedor
    aux_sets = []
    for pk, src in docs.items():
        if not src.tabular:
            continue
        t = src.main_table
        c = resolve_columns(t.headers, None, "masivo")
        aux_sets.append(AuxSet(name=src.name, sheet=t.sheet, headers=t.headers, cols=c,
                               rows=aux_ctx[3] if aux_ctx and src is aux_ctx[0] else build_aux_rows(t, c)))
    outputs = []
    errors = []
    active = plan.active_agents
    for i, agent in enumerate(active, start=1):
        ctl.stage(f"04 · Agente {AGENTES[agent]}", 60 + int(25 * i / max(len(active), 1)))
        if not aux_ctx and agent != "contratos":
            continue
        src, tab, cols, rows = aux_ctx if aux_ctx else (None, None, ColumnMap(group=-1, amount=-1), [])
        if agent == "contratos" and aux_ctx:
            cols = resolve_columns(tab.headers, run.columnas, "contratos")
            rows = build_aux_rows(tab, cols)
        ctx = AgentContext(
            source_name=src.name if src else "", sheet=tab.sheet if tab else "", headers=tab.headers if tab else [],
            cols=cols, rows=rows, params=params, sections=sections, cruce=cruce, aux_sets=aux_sets,
        )
        try:
            out = RUNNERS[agent](ctx)
        except AgentError as exc:
            errors.append(f"{AGENTES[agent]}: {exc}")
            for item in plan.items:
                if item.agent == agent:
                    item.active, item.reason = False, f"No se pudo ejecutar: {exc}"
            continue
        warnings += [f"{AGENTES[agent]}: {w}" for w in out.warnings]
        outputs.append(out)
    warnings += errors
    if not outputs and not sections:
        raise RunFailed(errors[0] if errors else "No hay nada que analizar: suba un auxiliar en Excel/CSV o documentos con texto.")

    # -- consolidación
    ctl.stage("05 · Consolidando resultados", 88)
    source_name = aux_ctx[0].name if aux_ctx else ""
    findings: list[Finding] = consolidate.cruce_findings(cruce, source_name)
    for out in outputs:
        findings += out.findings
    risk_table, hall_table = consolidate.findings_tables(findings)

    tables: list[Table] = []
    if cruce:
        tables.append(consolidate.cruce_table(cruce, source_name))
    for out in outputs:
        out.main.key = f"analisis:{out.agent}"
        out.main.title = f"ANÁLISIS · AGENTE {AGENTES[out.agent].upper()} · {out.main.title}"
        tables.append(out.main)
        for t in out.extras:
            t.key = f"{t.key}:{out.agent}"
            tables.append(t)
    if risk_table.rows:
        tables.append(risk_table)
    if hall_table.rows:
        tables.append(hall_table)

    exceptions = sum(o.exceptions for o in outputs)
    kpis = consolidate.summary_indicators(
        documents=len(docs), sections=len(classification.rows), fields=len(extraction.rows), cruce=cruce,
        exceptions=exceptions, risks=len(risk_table.rows), hallazgos=len(hall_table.rows),
    )
    conclusion = consolidate.conclusion_text([o.conclusion for o in outputs], cruce)
    conclusion_ia = False
    if ai.enabled and outputs:
        facts = {
            "indicadores": {k: (str(v) if isinstance(v, Decimal) else v) for k, v in kpis},
            "conclusion_base": conclusion,
            "alertas": [{"codigo": f.codigo, "resultado": f.resultado[:200], "nivel": f.alerta} for f in findings if f.codigo][:10],
        }
        drafted = ai.draft_conclusion(facts)
        if drafted:
            conclusion, conclusion_ia = drafted, True

    # -- guardado
    ctl.stage("05 · Guardando resultados", 93)
    ordered_findings = [f for f in findings if f.kind == "riesgo"] + [f for f in findings if f.kind == "hallazgo"]
    ordered_findings.sort(key=lambda f: (f.kind != "riesgo", f.codigo))
    integ: list[Table] = []
    if aux_ctx:
        src_, tab_, cols_, rows_ = aux_ctx
        integ = integration.build(src_.name, tab_.sheet, tab_.headers, cols_, rows_, tables, cruce)
    all_tables = tables + [classification, extraction] + integ
    # cifras con origen: las de los resultados y las de la integración que van al papel (resumen mensual y detalle corto)
    fig_tables = tables + [t for t in integ if t.key == "integracion_mes" or (t.key == "integracion" and len(t.rows) <= structured_fill.MAX_TABLE_ROWS)]
    counter = 0
    for fig in _walk_figs(fig_tables):
        counter += 1
        fig.fid = f"C-{counter:04d}"
    name_to_doc = {}
    for d in docs_db.values():
        name_to_doc.setdefault(d.nombre_original, d)

    with transaction.atomic():
        run.hallazgos.all().delete()
        run.cifras.all().delete()
        HallazgoAnalisis.objects.bulk_create(
            [
                HallazgoAnalisis(
                    corrida=run, orden=i, codigo=f.codigo, agente=f.agent, tipo=f.kind, procedimiento=f.procedimiento[:300],
                    resultado=f.resultado, importe=f.importe, fecha=f.fecha, origen=f.origen[:500], alerta=f.alerta, nia=f.nia[:80],
                    aseveracion=f.aseveracion[:120], condicion=f.condicion, criterio=f.criterio, causa=f.causa, efecto=f.efecto,
                    recomendacion=f.recomendacion,
                )
                for i, f in enumerate(ordered_findings, start=1)
            ]
        )
        CifraAnalisis.objects.bulk_create(
            [
                CifraAnalisis(
                    corrida=run, fid=fig.fid, etiqueta=(fig.label or "")[:200], valor=Decimal(str(fig.value)).quantize(Decimal("0.0001")),
                    documento=name_to_doc.get(fig.doc), documento_nombre=fig.doc[:255], hoja_origen=fig.sheet[:120], pagina=fig.page,
                    filas=fig.rows, agregacion=fig.agg, columna=fig.col, bbox=fig.bbox,
                )
                for fig in _walk_figs(fig_tables)
                if fig.value is not None
            ]
        )
        run.plan = plan.to_dict()
        run.plan["template"] = (
            {"sheets": template_info.sheets, "proposals": template_info.proposals, "formulas": template_info.formulas,
             "risks": template_info.risks, "macro": template_info.is_macro}
            if template_info else None
        )
        run.resumen = {"kpis": [[k, str(v)] for k, v in kpis], "excepciones": exceptions, "cruce_total": len(cruce)}
        run.tablas = {"orden": [t.key for t in all_tables], "tablas": {t.key: table_to_dict(t) for t in all_tables}}
        run.conclusion = conclusion
        run.conclusion_ia = conclusion_ia
        run.advertencias = warnings
        run.ai_llamadas = ai.calls
        run.save()

    # -- integrar en el papel de trabajo (si se subió uno) ANTES de marcar «Terminado»:
    #    así la pantalla nunca muestra un análisis terminado sin su papel de trabajo
    if template_doc:
        from . import services

        ctl.stage("06 · Integrando en el papel de trabajo", 96)
        try:
            services.paste_to_template(run, services.default_paste_options(), run.creado_por, motivo="Llenado automático",
                                       during_run=True)
        except services.PasteError as exc:
            run.advertencias = run.advertencias + [f"No se llenó el papel de trabajo: {exc}"]
            run.hallazgos.update(marcado_revision=True, destino_pt="⚑ Revisión")
    run.estado = CorridaAnalisis.Estado.TERMINADO
    run.progreso = 100
    run.etapa = "Terminado"
    run.terminado_en = timezone.now()
    run.save(update_fields=["estado", "progreso", "etapa", "terminado_en", "advertencias"])
    BitacoraAnalisis.registrar(
        run, run.creado_por, "terminada",
        {"agentes": [o.agent for o in outputs], "hallazgos": len(hall_table.rows), "riesgos": len(risk_table.rows), "ia_llamadas": ai.calls},
    )
