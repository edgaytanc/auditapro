from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

def superadmin_required(view_func):
    """
    Decorador que verifica si el usuario es un superAdmin.
    Si es superAdmin, permite el acceso a la vista.
    Si no es superAdmin, redirige a la página principal.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role and request.user.role.name == "superadmin":
            return view_func(request, *args, **kwargs)
        return redirect('dashboard')  # Redirigir a la página principal si no es superAdmin
    return _wrapped_view

def admin_or_superadmin_required(view_func):
    """
    Decorador que verifica si el usuario es un administrador o superAdmin.
    Si es administrador o superAdmin, permite el acceso a la vista.
    Si no es ninguno de los dos, redirige a la página principal.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role:
            if request.user.role.name in ["audit_manager", "superadmin"]:
                return view_func(request, *args, **kwargs)
        return redirect('dashboard')  # Redirigir a la página principal si no tiene permisos
    return _wrapped_view
