from functools import wraps

from django.http import (
    HttpResponseForbidden,
    JsonResponse,
)

from .models import RoleModulePermission


VALID_PERMISSION_ACTIONS = {
    "view",
    "create",
    "edit",
    "delete",
}


def get_user_role_name(user):
    """
    Retorna el nombre interno del rol del usuario.
    """

    role = getattr(
        user,
        "role",
        None,
    )

    return (
        getattr(role, "name", None)
        if role
        else None
    )


def is_team_manager(user):
    """
    Determina si el usuario es realmente
    un Jefe de Auditoría.

    No depende de que tenga modalidad grupal,
    porque también existen jefes individuales.
    """

    if not user or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    return (
        get_user_role_name(user)
        == "audit_manager"
    )


def has_module_permission(
    user,
    module,
    action,
):
    """
    Comprueba los permisos efectivos del usuario
    para un módulo y una acción determinada.
    """

    if action not in VALID_PERMISSION_ACTIONS:
        raise ValueError(
            f"La acción '{action}' no es válida."
        )

    if not user or not user.is_authenticated:
        return False

    # Administradores globales.
    if user.is_superuser or user.is_staff:
        return True

    # El Jefe de Auditoría conserva control total.
    if is_team_manager(user):
        return True

    role_id = getattr(
        user,
        "role_id",
        None,
    )

    owner_id = getattr(
        user,
        "administrador_id",
        None,
    )

    # Un integrante necesita rol y jefe asignados.
    if not role_id or not owner_id:
        return False

    permission_field = (
        f"can_{action}"
    )

    permission_value = (
        RoleModulePermission.objects
        .filter(
            owner_id=owner_id,
            role_id=role_id,
            module=module,
        )
        .values_list(
            permission_field,
            flat=True,
        )
        .first()
    )

    # Ante ausencia de configuración, se niega acceso.
    return permission_value is True


def module_permission_required(
    module,
    action,
):
    """
    Protege una vista mediante la Matriz de Permisos.
    """

    def decorator(view_function):

        @wraps(view_function)
        def wrapped_view(
            request,
            *args,
            **kwargs,
        ):
            allowed = has_module_permission(
                request.user,
                module,
                action,
            )

            if allowed:
                return view_function(
                    request,
                    *args,
                    **kwargs,
                )

            message = (
                "No tienes permiso para realizar "
                "esta acción."
            )

            requested_with = (
                request.headers.get(
                    "x-requested-with"
                )
            )

            if requested_with == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "message": message,
                    },
                    status=403,
                )

            return HttpResponseForbidden(
                message
            )

        return wrapped_view

    return decorator