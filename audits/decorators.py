from functools import wraps
from django.http import Http404, HttpRequest
from django.shortcuts import redirect, render
from audits.utils import get_selected_audit
from typing import Callable, Optional


def audit_manager_required(view_func):
    def check_roles(user) -> bool:
        return user.is_authenticated and (
            user.is_staff or user.role.name == "audit_manager"
        )

    @wraps(view_func)
    def wrapper(req, *args, **kwargs):
        if check_roles(req.user):
            return view_func(req, *args, **kwargs)
        else:
            raise Http404

    return wrapper


def group_admin_required(view_func):
    """
    Decorador que verifica que el usuario sea un administrador (audit_manager) 
    Y tenga modalidad grupal ('G').
    """
    def check_group_admin(user) -> bool:
        return user.is_authenticated and (
            (user.is_staff or user.role.name == "audit_manager") and 
            user.modalidad == 'G'
        )

    @wraps(view_func)
    def wrapper(req, *args, **kwargs):
        if check_group_admin(req.user):
            return view_func(req, *args, **kwargs)
        else:
            raise Http404

    return wrapper


def selected_audit_required(view_func_or_param: Optional[Callable] = None):
    def decorator(view_func: Callable, redirect_url=None):
        def check_selected_audit(req: HttpRequest):
            audit = req.session.get("selected_audit")
            return False if not audit else True

        @wraps(view_func)
        def wrapper(req: HttpRequest, *args, **kwargs):
            if req.GET.get("reload_audit") == "true":
                req.session["selected_audit"] = None

            if check_selected_audit(req):
                return view_func(req, *args, **kwargs)

            if req.POST.get("audit"):
                get_selected_audit(req)
                return view_func(req, *args, **kwargs)

            if redirect_url:
                return redirect(redirect_url)

            return render(req, "common/select-audit-page.html")

        return wrapper

    # Comprobar si el decorador fue llamado con una función directamente (sin paréntesis)
    if callable(view_func_or_param):
        return decorator(view_func_or_param)
    else:
        return lambda view_func: decorator(view_func, redirect_url=view_func_or_param)
