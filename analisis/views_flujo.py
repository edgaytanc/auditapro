"""Vistas de la fase 2: bandeja de hallazgos del proyecto, decisiones del jefe, informes y Monitoreo Continuo."""
from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from audits.models import Audit

from .flujo import config, monitoreo, services as fl
from .models import ArchivoProyecto, BitacoraProyecto, CorridaAnalisis, ExcepcionMonitoreo, Hallazgo
from .services import accessible_audits, accessible_runs

XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _audit_or_404(request, audit_id: int) -> Audit:
    return get_object_or_404(accessible_audits(request.user), pk=audit_id)


def _volver(audit_id: int):
    return redirect("analisis_hallazgos", audit_id=audit_id)


# ----------------------------------------------------------------------------- enviar desde un análisis
@login_required
@require_POST
def enviar_hallazgos(request, pk: int):
    run = get_object_or_404(accessible_runs(request.user), pk=pk)
    ids = [int(x) for x in request.POST.getlist("ids") if x.isdigit()]
    destino = request.POST.get("destino", "").strip()
    try:
        plazo = int(request.POST.get("plazo_dias") or 0) or None
    except ValueError:
        plazo = None
    over = {i: {"severidad": request.POST.get(f"sev_{i}", ""), "clasificacion": request.POST.get(f"clas_{i}", ""),
                "titulo": request.POST.get(f"titulo_{i}", ""), "responsable": request.POST.get("responsable", "")} for i in ids}
    over = {i: {k: v for k, v in d.items() if v} for i, d in over.items()}
    try:
        r = fl.enviar_a_papel(request.user, run, ids, destino=destino, overrides=over, plazo_dias=plazo)
    except fl.FlujoError as exc:
        messages.error(request, str(exc))
        return redirect("analisis_detalle", pk=run.pk)
    if r["enviados"]:
        messages.success(request, f"{len(r['enviados'])} hallazgo(s) enviados al papel de trabajo; sus evidencias van en la plantilla de Evidencias.")
    if r["duplicados"]:
        messages.warning(request, f"Ya estaban enviados y no se duplicaron: {', '.join(r['duplicados'])}.")
    return _volver(run.audit_id)


# ----------------------------------------------------------------------------- bandeja del proyecto
@login_required
@require_GET
def hallazgos_proyecto(request, audit_id: int):
    audit = _audit_or_404(request, audit_id)
    mod = fl.modulo_de(audit)
    fl.sincronizar_desde_plantillas(audit, request.user)
    hallazgos = list(fl.hallazgos_de(audit))
    for h in hallazgos:
        h.destino_nombre = fl.nombre_destino(h)
        h.estado_texto = fl.etiqueta_estado(h)
        h.ev_n = len(h.evidencias.all())
        h.puedo_decidir = (h.estado == config.EN_REVISION and fl.puede_decidir(request.user, audit)
                           and (fl.es_individual(audit) or h.creado_por_id != request.user.pk))
    archivos = [a for a in fl.archivos_actuales(audit)]
    historial = ArchivoProyecto.objects.filter(audit=audit).select_related("creado_por").order_by("-creado_en")[:40]
    areas = [(k, v["nombre"]) for k, v in config.areas_ai().items()] if mod == "I" else []
    return render(request, "analisis/hallazgos_proyecto.html", {
        "audit": audit, "modulo": mod, "modulo_nombre": config.NOMBRE_MODULO.get(mod, ""), "hallazgos": hallazgos, "archivos": archivos,
        "historial": historial, "resumen": fl.resumen_por_estado(audit), "etiquetas": config.ETIQUETA_ESTADO,
        "es_jefe": fl.puede_decidir(request.user, audit), "individual": fl.es_individual(audit), "areas": areas,
        "bitacora": BitacoraProyecto.objects.filter(audit=audit).select_related("usuario").order_by("-id")[:30],
        "cadena_valida": BitacoraProyecto.cadena_valida(audit),
        "hay_aprobados": any(h.estado in (config.APROBADO, config.INCLUIDO) for h in hallazgos),
        "areas_con_hallazgos": sorted({(h.area, h.destino_nombre) for h in hallazgos if h.modulo == "I" and h.area and h.area != "transversal"
                                       and h.estado in (config.APROBADO, config.INCLUIDO)}),
        "tiene_monitoreo": mod == "I",
    })


@login_required
@require_POST
def a_revision(request, audit_id: int):
    audit = _audit_or_404(request, audit_id)
    ids = [int(x) for x in request.POST.getlist("ids") if x.isdigit()]
    try:
        r = fl.enviar_a_revision(request.user, audit, ids)
        messages.success(request, f"{len(r['enviados'])} hallazgo(s) enviados a revisión.")
    except fl.FlujoError as exc:
        messages.error(request, str(exc))
    return _volver(audit.pk)


@login_required
@require_POST
def decidir_hallazgo(request, audit_id: int, hid: int):
    audit = _audit_or_404(request, audit_id)
    h = get_object_or_404(Hallazgo, pk=hid, audit=audit)
    try:
        fl.decidir(request.user, h, request.POST.get("decision", ""), request.POST.get("comentario", ""))
        messages.success(request, f"Hallazgo {h.ref_local}: decisión registrada.")
    except fl.FlujoError as exc:
        messages.error(request, str(exc))
    return _volver(audit.pk)


@login_required
@require_POST
def reabrir_hallazgo(request, audit_id: int, hid: int):
    audit = _audit_or_404(request, audit_id)
    h = get_object_or_404(Hallazgo, pk=hid, audit=audit)
    try:
        fl.reabrir(request.user, h, request.POST.get("comentario", ""))
        messages.success(request, f"Hallazgo {h.ref_local} reabierto: vuelve a revisión.")
    except fl.FlujoError as exc:
        messages.error(request, str(exc))
    return _volver(audit.pk)


@login_required
@require_POST
def generar_informe(request, audit_id: int):
    """«Aprobar hallazgos finales» (Financiera) · «Regenerar hallazgos del informe» (Interna) · «Regenerar sección 7» (Revisoría)."""
    audit = _audit_or_404(request, audit_id)
    try:
        if fl.modulo_de(audit) == "F" and request.POST.get("accion") != "regenerar":
            r = fl.aprobar_finales(request.user, audit)
            messages.success(request, f"{r['hallazgos']} hallazgo(s) finales; informe nuevo: {r['informe'].nombre}.")
        else:
            reg = fl.regenerar(request.user, audit, request.POST.get("area", ""))
            messages.success(request, f"Se generó {reg.nombre}; la versión anterior se conserva.")
    except fl.FlujoError as exc:
        messages.error(request, str(exc))
    return _volver(audit.pk)


@login_required
@require_POST
def sincronizar(request, audit_id: int):
    audit = _audit_or_404(request, audit_id)
    cambios = fl.sincronizar_desde_plantillas(audit, request.user)
    messages.success(request, f"Se leyeron las plantillas: {len(cambios)} cambio(s) del auditor incorporados.")
    return _volver(audit.pk)


@login_required
@require_GET
def descargar_archivo(request, audit_id: int, pk: int):
    audit = _audit_or_404(request, audit_id)
    arch = get_object_or_404(ArchivoProyecto, pk=pk, audit=audit)
    BitacoraProyecto.registrar(audit, request.user, "descarga", "archivo", arch.nombre)
    tipo = DOCX_TYPE if arch.nombre.lower().endswith(".docx") else XLSX_TYPE
    return FileResponse(arch.archivo.open("rb"), as_attachment=True, filename=Path(arch.nombre).name, content_type=tipo)


# ----------------------------------------------------------------------------- Monitoreo Continuo (Auditoría Interna)
def _interna_or_404(request, audit_id: int) -> Audit:
    audit = _audit_or_404(request, audit_id)
    if fl.modulo_de(audit) != "I":
        raise Http404("Monitoreo Continuo es de Auditoría Interna.")
    return audit


@login_required
@require_GET
def monitoreo_panel(request, audit_id: int):
    audit = _interna_or_404(request, audit_id)
    sel = request.GET.get("caso")
    lista = monitoreo.lista(audit)
    elegido = next((e for e in lista if str(e.pk) == sel), None)
    for e in lista:
        e.seg = monitoreo._seguimiento_estado(e)
    if elegido:
        elegido.seg = monitoreo._seguimiento_estado(elegido)
        elegido.hallazgo_obj = elegido.hallazgo
    return render(request, "analisis/monitoreo.html", {
        "audit": audit, "panel": monitoreo.panel(audit), "lista": lista, "elegido": elegido,
        "areas": [(k, v["nombre"]) for k, v in config.areas_ai().items()],
        "area_sugerida": monitoreo.area_sugerida(elegido) if elegido else "",
    })


@login_required
@require_POST
def monitoreo_accion(request, audit_id: int, pk: int):
    audit = _interna_or_404(request, audit_id)
    ex = get_object_or_404(ExcepcionMonitoreo, pk=pk, audit=audit)
    accion = request.POST.get("accion")
    try:
        if accion == "confirmar":
            monitoreo.confirmar(request.user, ex)
            messages.success(request, f"{ex.caso} confirmada: seguimiento asignado a 7 días.")
        elif accion == "descartar":
            monitoreo.descartar(request.user, ex)
            messages.success(request, f"{ex.caso} marcada como falso positivo.")
        elif accion == "ampliar":
            monitoreo.ampliar_plazo(request.user, ex)
            messages.success(request, f"Plazo de {ex.caso} ampliado 5 días.")
        elif accion == "hallazgo":
            h = monitoreo.convertir_en_hallazgo(request.user, ex, request.POST.get("area", ""))
            messages.success(request, f"Hallazgo {h.ref_local} creado y enviado a las plantillas de Hallazgos y Evidencias.")
        else:
            messages.error(request, "Acción no válida.")
    except (monitoreo.MonitoreoError, fl.FlujoError) as exc:
        messages.error(request, str(exc))
    return redirect(f"{reverse('analisis_monitoreo', args=[audit.pk])}?caso={ex.pk}")


@login_required
@require_GET
def monitoreo_descarga(request, audit_id: int, pk: int, formato: str):
    audit = _interna_or_404(request, audit_id)
    ex = get_object_or_404(ExcepcionMonitoreo, pk=pk, audit=audit)
    nombre = ex.caso.lstrip("#")
    if formato == "xlsx":
        data, tipo = monitoreo.excel_excepcion(ex), XLSX_TYPE
    elif formato == "docx":
        data, tipo = monitoreo.word_excepcion(ex), DOCX_TYPE
    elif formato == "pdf":
        data, tipo = monitoreo.pdf_excepcion(ex), "application/pdf"
    else:
        raise Http404
    BitacoraProyecto.registrar(audit, request.user, "monitoreo_descarga", "excepcion", ex.caso, {}, {"formato": formato})
    resp = HttpResponse(data, content_type=tipo)
    resp["Content-Disposition"] = f'attachment; filename="Excepcion_{nombre}.{formato}"'
    return resp


@login_required
@require_GET
def monitoreo_descarga_panel(request, audit_id: int):
    audit = _interna_or_404(request, audit_id)
    resp = HttpResponse(monitoreo.excel_panel(audit), content_type=XLSX_TYPE)
    resp["Content-Disposition"] = 'attachment; filename="Monitoreo_Continuo.xlsx"'
    return resp
