from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.exceptions import SuspiciousOperation
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.conf import settings
from pathlib import Path

from .claude_service import (
    ErrorEntradaIA, ErrorProveedorIA, preparar_adjuntos,
    consultar_claude, verificar_configuracion,
)
from .quota import SinCupo, devolver_consulta, obtener_cupo, reservar_consulta
from .upload_handlers import MAX_BODY_BYTES


@login_required
@require_GET
@never_cache
def audita_analisis(request):
    cupo = obtener_cupo(request.user)
    return render(request, "common/v2/audita_analisis_demo.html", {
        "cupo_restante": cupo.restantes,
        "cupo_realizadas": cupo.realizadas,
        "email_actual": request.user.email or request.user.username,
    })


@login_required
@require_POST
@csrf_protect
@never_cache
def enviar_consulta(request):
    """No graba archivos, preguntas o respuestas. Solo persisten contadores de cuota."""
    if not request.user.is_active or getattr(request.user, "is_deleted", False):
        return JsonResponse({"error": "Cuenta deshabilitada."}, status=403)

    # Los POST multipart grandes se rechazan ANTES de invocar request.FILES.
    try:
        longitud = int(request.META.get("CONTENT_LENGTH") or "0")
    except (ValueError, TypeError):
        return JsonResponse({"error": "Longitud de la solicitud inválida."}, status=400)
    if longitud > MAX_BODY_BYTES:
        return JsonResponse({"error": "Solicitud demasiado grande (límite 6 MiB)."}, status=413)
    if "multipart/form-data" not in request.content_type.lower():
        return JsonResponse({"error": "Utiliza el formulario de consulta con multipart/form-data."}, status=415)

    # Un usuario sin créditos no debe forzar trabajo de extracción de archivos.
    if obtener_cupo(request.user).restantes == 0:
        return JsonResponse({"error": "Has utilizado tus 5 consultas. Solicita una recarga al administrador.", "restantes": 0}, status=429)

    # El middleware ya instaló el handler RAM antes de CSRF y del parseo POST.
    try:
        pregunta = request.POST.get("pregunta", "").strip()
        archivos = request.FILES.getlist("archivos")
        if archivos:
            return JsonResponse({"error": "Por el momento solo se permiten consultas de texto."}, status=400)
        if not pregunta or len(pregunta) > 1800:
            return JsonResponse({"error": "Escribe una pregunta de entre 1 y 1800 caracteres."}, status=400)
        adjuntos = preparar_adjuntos(archivos)
        verificar_configuracion()
    except ErrorEntradaIA as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ErrorProveedorIA as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except (SuspiciousOperation, ValueError) as exc:
        return JsonResponse({"error": "Solicitud o archivo no válido."}, status=400)

    try:
        cupo_id, version = reservar_consulta(request.user)
    except SinCupo:
        return JsonResponse({"error": "Has utilizado tus 5 consultas. Solicita una recarga al administrador.", "restantes": 0}, status=429)

    try:
        respuesta = consultar_claude(pregunta, adjuntos)
    except ErrorProveedorIA as exc:
        devolver_consulta(cupo_id, version)
        return JsonResponse({"error": str(exc), "restantes": obtener_cupo(request.user).restantes}, status=503)
    except Exception:
        # No se filtran al usuario detalles del proveedor ni datos de archivos.
        devolver_consulta(cupo_id, version)
        return JsonResponse({"error": "Error temporal al generar la respuesta. Cupo reintegrado.", "restantes": obtener_cupo(request.user).restantes}, status=503)

    cupo = obtener_cupo(request.user)
    return JsonResponse({"respuesta": respuesta, "restantes": cupo.restantes, "realizadas": cupo.realizadas})


@login_required
@require_GET
@never_cache
def consultas(request):
    """Muestra únicamente el entorno local original de Consultas del cliente."""
    return render(request, "analisis_ia/consultas.html")


@login_required
@require_GET
@never_cache
@xframe_options_sameorigin
def consultas_entorno(request):
    """Entrega el HTML guiado, sin servicios externos de IA ni contador de backend."""
    document_path = Path(settings.BASE_DIR) / "analisis_ia" / "templates" / "analisis_ia" / "consulta_workspace.html"
    html = document_path.read_text(encoding="utf-8")
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response
