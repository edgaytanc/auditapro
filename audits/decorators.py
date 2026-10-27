from functools import wraps
from typing import Callable, Optional

from django.http import (
    Http404,
    HttpRequest,
)
from django.shortcuts import (
    redirect,
    render,
)

from users.permissions import (
    has_module_permission,
    is_team_manager,
)


def audit_manager_required(
    view_func,
):
    """
    Permite únicamente a:

    - Jefes de Auditoría.
    - Superusuarios.
    - Usuarios staff.
    """

    @wraps(view_func)
    def wrapper(
        req,
        *args,
        **kwargs,
    ):
        allowed = (
            req.user.is_authenticated
            and (
                req.user.is_superuser
                or req.user.is_staff
                or is_team_manager(
                    req.user
                )
            )
        )

        if allowed:
            return view_func(
                req,
                *args,
                **kwargs,
            )

        raise Http404

    return wrapper


def group_admin_required(
    view_func,
):
    """
    Permite únicamente a un Jefe de Auditoría
    con modalidad grupal.
    """

    @wraps(view_func)
    def wrapper(
        req,
        *args,
        **kwargs,
    ):
        allowed = (
            req.user.is_authenticated
            and (
                req.user.is_superuser
                or req.user.is_staff
                or (
                    is_team_manager(
                        req.user
                    )
                    and req.user.modalidad
                    == "G"
                )
            )
        )

        if allowed:
            return view_func(
                req,
                *args,
                **kwargs,
            )

        raise Http404

    return wrapper


def _user_has_module_action(
    user,
    module,
    action,
):
    """
    Comprueba el permiso general antes de mostrar
    o procesar una auditoría seleccionada.
    """

    if (
        not user
        or not user.is_authenticated
    ):
        return False

    if (
        user.is_superuser
        or user.is_staff
        or is_team_manager(user)
    ):
        return True

    return has_module_permission(
        user,
        module,
        action,
    )


def _clear_selected_audit(
    req,
):
    """
    Elimina de la sesión una selección inválida,
    vencida o perteneciente a otro equipo.
    """

    req.session.pop(
        "selected_audit",
        None,
    )

    req.session.modified = True


def _get_session_audit_id(
    req,
):
    """
    Obtiene de forma segura el ID almacenado
    en la sesión.
    """

    selected_audit = req.session.get(
        "selected_audit"
    )

    if not selected_audit:
        return None

    if isinstance(
        selected_audit,
        dict,
    ):
        audit_id = selected_audit.get(
            "id"
        )

    else:
        audit_id = getattr(
            selected_audit,
            "id",
            None,
        )

    try:
        return int(
            audit_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def selected_audit_required(
    view_func_or_param: Optional[
        Callable
    ] = None,
    *,
    module="workpapers",
    action="view",
):
    """
    Exige una auditoría seleccionada y valida
    nuevamente su acceso en cada solicitud.

    Uso tradicional:

        @selected_audit_required
        def vista(...):
            ...

        @selected_audit_required(
            "ruta_de_retorno"
        )
        def vista(...):
            ...

    Uso con acción específica:

        @selected_audit_required(
            "ruta_de_retorno",
            module="workpapers",
            action="edit",
        )
        def vista(...):
            ...

    Reglas:
    - La auditoría debe existir.
    - Debe pertenecer al mismo equipo.
    - El integrante debe estar asignado.
    - Debe tener permiso en la matriz.
    - Jefes, superusuarios y staff mantienen
      acceso administrativo.
    """

    def decorator(
        view_func: Callable,
        redirect_url=None,
    ):
        def authorize_audit(
            req,
            audit_id,
        ):
            # Imports locales para evitar ciclos.
            from audits.access import (
                get_audit_for_user_or_404,
            )
            from audits.utils import (
                audit_to_dict,
            )

            audit = (
                get_audit_for_user_or_404(
                    req.user,
                    audit_id,
                    action=action,
                    module=module,
                )
            )

            # Refresca la información de sesión
            # usando los datos actuales de la BD.
            req.session[
                "selected_audit"
            ] = audit_to_dict(
                audit
            )

            req.session.modified = True

            # También queda disponible como objeto
            # durante la solicitud actual.
            req.selected_audit = audit

            return audit

        def render_selection_page(
            req,
            redirect_url=None,
        ):
            if redirect_url:
                return redirect(
                    redirect_url
                )

            role = getattr(
                req.user,
                "role",
                None,
            )

            role_name = getattr(
                role,
                "name",
                "",
            )

            # Import local para evitar ciclos.
            from audits.utils import (
                get_assigned_audits,
            )

            assigned_audits = (
                get_assigned_audits(
                    user_role=role_name,
                    req=req,
                )
            )

            return render(
                req,
                (
                    "common/"
                    "select-audit-page.html"
                ),
                {
                    "assigned_audits": (
                        assigned_audits
                    ),
                },
            )

        @wraps(view_func)
        def wrapper(
            req: HttpRequest,
            *args,
            **kwargs,
        ):
            if not _user_has_module_action(
                req.user,
                module,
                action,
            ):
                raise Http404

            if (
                req.GET.get(
                    "reload_audit"
                )
                == "true"
            ):
                _clear_selected_audit(
                    req
                )

            posted_audit_id = (
                req.POST.get(
                    "audit"
                )
            )

            if posted_audit_id:
                try:
                    authorize_audit(
                        req,
                        posted_audit_id,
                    )

                except (
                    Http404,
                    TypeError,
                    ValueError,
                ):
                    _clear_selected_audit(
                        req
                    )

                    raise Http404

                return view_func(
                    req,
                    *args,
                    **kwargs,
                )

            session_audit_id = (
                _get_session_audit_id(
                    req
                )
            )

            if session_audit_id is not None:
                try:
                    authorize_audit(
                        req,
                        session_audit_id,
                    )

                except (
                    Http404,
                    TypeError,
                    ValueError,
                ):
                    _clear_selected_audit(
                        req
                    )

                    return render_selection_page(
                        req,
                        redirect_url=(
                            redirect_url
                        ),
                    )

                return view_func(
                    req,
                    *args,
                    **kwargs,
                )

            _clear_selected_audit(
                req
            )

            return render_selection_page(
                req,
                redirect_url=redirect_url,
            )

        return wrapper

    if callable(
        view_func_or_param
    ):
        return decorator(
            view_func_or_param
        )

    return lambda view_func: decorator(
        view_func,
        redirect_url=(
            view_func_or_param
        ),
    )