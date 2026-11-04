from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import jobs, services
from .engine.normalize import fmt_num
from .engine.shared import Fig, dec
from .forms import ComentarioForm, DecisionForm, NuevoAnalisisForm, PegarForm
from .models import BitacoraAnalisis, CifraAnalisis, CorridaAnalisis
from .validators import UploadRejected, allowed_extensions

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLSM_TYPE = "application/vnd.ms-excel.sheet.macroEnabled.12"

HIDDEN_IN_UI = {"clasificacion", "extraccion", "riesgos", "hallazgos", "integracion", "integracion_mes"}


def _run_or_404(request, pk: int) -> CorridaAnalisis:
    return get_object_or_404(services.accessible_runs(request.user), pk=pk)


# --------------------------------------------------------------------------- presentación

def _kpi(value: str) -> str:
    """Importes con separador de miles (los conteos se dejan tal cual)."""
    try:
        d = Decimal(value)
    except Exception:  # noqa: BLE001
        return value
    return fmt_num(d) if "." in value else value


def _cell(value) -> dict:
    """Celda lista para la plantilla: texto, alineación y, si es cifra, su id."""
    fid = ""
    if isinstance(value, Fig):
        fid, value = value.fid, value.value
    if value is None:
        text, num = "", False
    elif isinstance(value, Decimal):
        text, num = fmt_num(value), True
    elif isinstance(value, bool):
        text, num = str(value), False
    elif isinstance(value, (int, float)):
        text, num = (f"{value:,}" if isinstance(value, int) else f"{value:,.2f}"), True
    elif isinstance(value, (date, datetime)):
        text, num = value.strftime("%d/%m/%Y"), False
    else:
        text, num = str(value), False
    return {"text": text, "num": num, "fid": fid}


def _tables_for_ui(run: CorridaAnalisis) -> list[dict]:
    data = run.tablas or {}
    out = []
    for key in data.get("orden", []):
        if key in HIDDEN_IN_UI and key not in ("clasificacion", "extraccion"):
            continue
        t = data["tablas"][key]
        rows = [[_cell(dec(c)) for c in row] for row in t["rows"]]
        out.append(
            {"key": key, "title": t["title"], "head": t["head"], "rows": list(zip(rows, t["flags"] or [""] * len(rows))),
             "note": t["note"], "truncated": t["truncated"], "flagged": t["flagged"], "support": key in ("clasificacion", "extraccion")}
        )
    return out


# --------------------------------------------------------------------------- páginas

@login_required
@require_GET
def home(request):
    jobs.mark_stale()
    runs = services.accessible_runs(request.user)[:60]
    return render(request, "analisis/home.html", {"runs": runs, "tiene_proyectos": services.accessible_audits(request.user).exists()})


@login_required
def nuevo(request):
    if request.method == "POST":
        form = NuevoAnalisisForm(request.user, request.POST)
        if form.is_valid():
            problem = jobs.capacity_error(request.user)
            if problem:
                messages.error(request, problem)
            else:
                try:
                    run = services.create_run(
                        request.user, form.cleaned_data["audit"],
                        titulo=form.cleaned_data["titulo"], instruccion=form.cleaned_data["instruccion"],
                        agentes=form.cleaned_data["agentes"], parametros=form.parametros(),
                        plantilla=request.FILES.get("plantilla"), auxiliares=request.FILES.getlist("auxiliares"),
                        soportes=request.FILES.getlist("soportes"),
                    )
                except UploadRejected as exc:
                    messages.error(request, str(exc))
                else:
                    run.columnas = form.columnas()
                    run.save(update_fields=["columnas"])
                    jobs.submit(run.pk)
                    messages.success(request, "Análisis iniciado. Puede seguir el avance en esta página.")
                    return redirect("analisis_detalle", pk=run.pk)
    else:
        form = NuevoAnalisisForm(request.user)
    return render(request, "analisis/nuevo.html", {"form": form, "extensiones": ", ".join(allowed_extensions())})


@login_required
@require_GET
def detalle(request, pk: int):
    jobs.mark_stale()
    run = _run_or_404(request, pk)
    version = run.ultima_version
    plan = run.plan or {}
    template_info = plan.get("template") or {}
    validation = (run.resumen or {}).get("validacion")
    context = {
        "run": run,
        "plan": plan,
        "kpis": [[k, _kpi(v)] for k, v in (run.resumen or {}).get("kpis", [])],
        "tablas": _tables_for_ui(run) if run.estado == CorridaAnalisis.Estado.TERMINADO else [],
        "hallazgos": list(run.hallazgos.all()),
        "documentos": run.documentos.all(),
        "versiones": run.versiones.all(),
        "version": version,
        "plantilla": run.plantilla,
        "template_info": template_info,
        "validation": validation,
        "cifras_pendientes": list(run.cifras.exclude(estado=CifraAnalisis.Estado.VERIFICADA).exclude(estado=CifraAnalisis.Estado.PENDIENTE)[:30]),
        "bitacora": run.bitacora.select_related("usuario").order_by("-id")[:25],
        "cadena_valida": BitacoraAnalisis.cadena_valida(run),
        "puede_aprobar": services.can_approve(request.user, run),
        "terminado": run.estado == CorridaAnalisis.Estado.TERMINADO,
        "aprobado": run.revision == CorridaAnalisis.Revision.APROBADO,
    }
    return render(request, "analisis/detalle.html", context)


@login_required
@require_GET
def estado(request, pk: int):
    jobs.mark_stale()
    run = _run_or_404(request, pk)
    return JsonResponse(
        {"estado": run.estado, "etiqueta": run.get_estado_display(), "etapa": run.etapa, "progreso": run.progreso,
         "error": run.error_mensaje}
    )


@login_required
@require_POST
def parar(request, pk: int):
    run = _run_or_404(request, pk)
    if run.activa:
        run.estado = CorridaAnalisis.Estado.DETENIDO
        run.terminado_en = timezone.now()
        run.save(update_fields=["estado", "terminado_en"])
        BitacoraAnalisis.registrar(run, request.user, "detenida_por_usuario", {})
        messages.success(request, "Análisis detenido.")
    return redirect("analisis_detalle", pk=run.pk)


@login_required
@require_POST
def pegar(request, pk: int):
    run = _run_or_404(request, pk)
    form = PegarForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise los datos del formulario.")
        return redirect("analisis_detalle", pk=run.pk)
    try:
        version = services.paste_to_template(run, form.options(), request.user, motivo="Pegado manual")
    except services.PasteError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Papel de trabajo llenado: {version.nombre}. Su original quedó intacto.")
    return redirect("analisis_detalle", pk=run.pk)


@login_required
@require_GET
def descargar(request, pk: int, numero: int | None = None):
    run = _run_or_404(request, pk)
    versions = run.versiones.all()
    version = get_object_or_404(versions, numero=numero) if numero else versions.first()
    if version is None:
        raise Http404("Aún no hay una versión del papel de trabajo.")
    BitacoraAnalisis.registrar(run, request.user, "descarga", {"version": version.numero, "archivo": version.nombre})
    kind = XLSM_TYPE if version.nombre.lower().endswith(".xlsm") else XLSX_TYPE
    return FileResponse(version.archivo.open("rb"), as_attachment=True, filename=Path(version.nombre).name, content_type=kind)


@login_required
@require_GET
def resultados_csv(request, pk: int):
    run = _run_or_404(request, pk)
    response = HttpResponse(services.results_csv(run), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="resultados_analisis_{run.pk}.csv"'
    return response


@login_required
@require_POST
def validar(request, pk: int):
    run = _run_or_404(request, pk)
    if run.estado != CorridaAnalisis.Estado.TERMINADO:
        messages.error(request, "El análisis aún no termina.")
    else:
        summary = services.validate_figures(run, request.user)
        messages.success(
            request,
            f"Validación: {summary['verificadas']} de {summary['total']} cifras cuadran con su origen; "
            f"{summary['no_cuadran']} no cuadran, {summary['cambio']} cambiaron de origen, {summary['sin_origen']} no se pueden verificar.",
        )
    return redirect("analisis_detalle", pk=run.pk)


@login_required
@require_POST
def aprobar(request, pk: int):
    run = _run_or_404(request, pk)
    form = ComentarioForm(request.POST)
    try:
        services.approve_run(run, request.user, form.data.get("comentario", ""))
    except services.ApprovalError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Resultado aprobado. Queda en el expediente con su trazabilidad.")
    return redirect("analisis_detalle", pk=run.pk)


@login_required
@require_POST
def rechazar(request, pk: int):
    run = _run_or_404(request, pk)
    try:
        services.reject_run(run, request.user, request.POST.get("comentario", ""))
    except services.ApprovalError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Resultado rechazado. Ajuste los parámetros y vuelva a ejecutar el análisis.")
    return redirect("analisis_detalle", pk=run.pk)


@login_required
@require_POST
def decidir(request, pk: int, hid: int):
    run = _run_or_404(request, pk)
    finding = get_object_or_404(run.hallazgos, pk=hid)
    form = DecisionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Decisión no válida.")
    else:
        try:
            services.decide_finding(finding, request.user, form.cleaned_data["decision"], form.cleaned_data["nota"])
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"{finding.codigo}: decisión registrada.")
    return redirect("analisis_detalle", pk=run.pk)


# --------------------------------------------------------------------------- visor de origen

@login_required
@require_GET
def cifra_origen(request, pk: int, fid: str):
    run = _run_or_404(request, pk)
    c = get_object_or_404(run.cifras, fid=fid)
    data = {
        "fid": c.fid, "etiqueta": c.etiqueta, "valor": f"{c.valor:.2f}", "documento": c.documento_nombre,
        "hoja": c.hoja_origen, "pagina": c.pagina, "filas": c.filas[:20], "agregacion": c.agregacion,
        "celda": f"{c.hoja_destino}!{c.celda}" if c.celda else "", "estado": c.get_estado_display(), "detalle": c.detalle,
        "tiene_imagen": bool(c.pagina and c.documento and c.documento.formato == "pdf"),
    }
    if c.filas and c.documento and c.documento.formato in ("excel", "csv"):
        src = services._Source(run)
        rows = src.rows(c.documento_nombre, c.hoja_origen)
        tab = src.tab(c.documento_nombre, c.hoja_origen)
        wanted = sorted(set(c.filas[:5]))
        context_rows = []
        for n in wanted:
            for m in (n - 1, n, n + 1):
                if m in rows and m not in [r["fila"] for r in context_rows]:
                    context_rows.append({"fila": m, "valores": [str(v) if v is not None else "" for v in rows[m]], "citada": m in c.filas})
        data["encabezados"] = tab.headers if tab else []
        data["vecinas"] = sorted(context_rows, key=lambda r: r["fila"])
    return JsonResponse(data)


@login_required
@require_GET
def cifra_pagina(request, pk: int, fid: str):
    """Página del PDF de origen con el rectángulo de la cifra resaltado."""
    run = _run_or_404(request, pk)
    c = get_object_or_404(run.cifras, fid=fid)
    if not (c.pagina and c.documento and c.documento.formato == "pdf"):
        raise Http404
    import pdfplumber

    with pdfplumber.open(c.documento.archivo.path) as pdf:
        if not 1 <= c.pagina <= len(pdf.pages):
            raise Http404
        image = pdf.pages[c.pagina - 1].to_image(resolution=90)
        if c.bbox:
            image.draw_rect((c.bbox["x0"], c.bbox["top"], c.bbox["x1"], c.bbox["bottom"]), stroke=(220, 38, 38, 255), stroke_width=2, fill=(255, 235, 59, 70))
        buf = io.BytesIO()
        image.annotated.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")
