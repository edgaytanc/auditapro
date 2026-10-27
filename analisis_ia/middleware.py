"""Interviene antes de CsrfViewMiddleware, que puede leer POST y archivos."""
from django.http import JsonResponse

from .upload_handlers import MAX_BODY_BYTES, SoloMemoriaLimitada


class SoloMemoriaAnalisisMiddleware:
    """Evita que CsrfViewMiddleware active TemporaryFileUploadHandler."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path_info == "/audita-analisis/consultar/":
            try:
                tamano = int(request.META.get("CONTENT_LENGTH") or "0")
            except (TypeError, ValueError):
                return JsonResponse({"error": "Tamaño de solicitud inválido."}, status=400)
            if tamano > MAX_BODY_BYTES:
                return JsonResponse({"error": "Solicitud demasiado grande (límite 6 MiB)."}, status=413)
            request.upload_handlers = [SoloMemoriaLimitada(request)]
        return self.get_response(request)
