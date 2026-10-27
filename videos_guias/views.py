from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .catalog import GUIDES, GUIDES_BY_SLUG, PRESENTATIONS, VIDEOS, YOUTUBE_CHANNEL, YOUTUBE_VIDEOS


GUIDES_DIR = Path(__file__).resolve().parent / "guides"


@login_required
@require_GET
def index(request):
    """Pantalla informativa; no modifica auditorías ni datos del usuario."""
    return render(
        request,
        "videos_guias/index.html",
        {
            "videos": VIDEOS,
            "presentations": PRESENTATIONS,
            "guides": GUIDES,
            "youtube_channel": YOUTUBE_CHANNEL,
            "youtube_videos": YOUTUBE_VIDEOS,
        },
    )


@login_required
@require_GET
def guide_pdf(request, slug):
    """Sirve una guía incluida en el módulo a usuarios autenticados."""
    guide = GUIDES_BY_SLUG.get(slug)
    if guide is None:
        raise Http404("Guía no encontrada")

    pdf_path = GUIDES_DIR / guide["filename"]
    if not pdf_path.is_file():
        raise Http404("Archivo de guía no disponible")

    return FileResponse(
        pdf_path.open("rb"),
        content_type="application/pdf",
        filename=guide["filename"],
        as_attachment=False,
    )
