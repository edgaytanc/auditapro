"""Recarga desde Superadmin ORIGINAL: usa su template base, no toca el menú v2."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .models import CupoConsultasIA
from .quota import obtener_cupo, recargar_cinco


@login_required
@require_http_methods(["GET", "POST"])
def administrar_cupos(request):
    usuario_actual = request.user
    rol = getattr(getattr(usuario_actual, "role", None), "name", "")
    if not usuario_actual.is_active or getattr(usuario_actual, "is_deleted", False) or not (
        usuario_actual.is_superuser or rol == "superadmin"
    ):
        return HttpResponseForbidden("Acceso reservado al Superadministrador.")

    User = get_user_model()
    if request.method == "POST":
        usuario_id = request.POST.get("usuario_id", "")
        if not usuario_id.isdigit():
            messages.error(request, "Usuario inválido.")
        else:
            objetivo = User.objects.filter(pk=int(usuario_id), is_active=True, is_deleted=False).first()
            if objetivo is None:
                messages.error(request, "Usuario inexistente o desactivado.")
            else:
                recargar_cinco(objetivo)
                messages.success(request, f"Cupo restaurado a 5 para {objetivo.email or objetivo.username}.")
        return redirect("audita_analisis_cupos")

    busqueda = request.GET.get("q", "").strip()[:100]
    qs = User.objects.filter(is_active=True, is_deleted=False).order_by("email", "pk")
    if busqueda:
        qs = qs.filter(Q(email__icontains=busqueda) | Q(username__icontains=busqueda))
    pag = Paginator(qs, 25).get_page(request.GET.get("page"))
    cuotas = {c.usuario_id: c for c in CupoConsultasIA.objects.filter(usuario_id__in=[u.pk for u in pag])}
    registros = [{"usuario": u, "restantes": cuotas[u.pk].restantes if u.pk in cuotas else 5} for u in pag]
    return render(request, "analisis_ia/admin_cupos.html", {
        "registros": registros, "pagina": pag, "busqueda": busqueda,
    })
