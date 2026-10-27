"""Pantalla manual del Archivo Permanente: no lee ni modifica expedientes Audit."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from users.permissions import has_module_permission, is_team_manager


@login_required
def archivo_manual(request):
    """Reutiliza el shell y la autenticación; los datos viven en localStorage."""
    if not (
        request.user.is_superuser
        or request.user.is_staff
        or is_team_manager(request.user)
        or has_module_permission(request.user, "workpapers", "view")
    ):
        raise PermissionDenied("No tiene acceso al Archivo Permanente.")
    return render(request, "archivo/archivo_permanente_manual.html")
