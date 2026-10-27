from urllib.parse import urlsplit

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .enlaces import ENLACES


@login_required
@require_GET
def mejorar_plan(request):
    """Catálogo: pestañas Individual y Grupos; no altera la suscripción."""
    return render(request, "planes/mejorar.html")


@login_required
@require_GET
def renovacion(request):
    """Ofrece la renovación; la fecha de expiración no existe en el modelo actual."""
    return render(request, "planes/renovacion.html")


@login_required
@require_GET
def comprar(request, plan):
    """Solo redirige al proveedor. NO activa el plan ni registra un pago."""
    enlace = ENLACES.get(plan)
    if enlace is None:
        raise Http404("Plan desconocido")
    destino = urlsplit(enlace)
    if destino.scheme != "https" or destino.netloc != "app.recurrente.com":
        return HttpResponseBadRequest("Enlace de pago mal configurado")
    return HttpResponseRedirect(enlace)
