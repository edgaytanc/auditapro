"""Vistas de demostración, sin integración con servicios de inteligencia artificial."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET


@login_required
@require_GET
def audita_analisis_demo(request):
    """Muestra únicamente el prototipo solicitado por el cliente."""
    return render(request, "common/v2/audita_analisis_demo.html")
