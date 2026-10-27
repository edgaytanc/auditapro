from django.http import Http404
from django.shortcuts import get_object_or_404

from users.permissions import (
    has_module_permission,
    is_team_manager,
)

from .models import Audit


OPERATIONAL_ROLES = {
    "auditor",
    "supervisor",
    "readonly",
}


def get_user_role_name(user):
    """
    Retorna el nombre interno del rol.
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


def get_team_owner(user):
    """
    Obtiene el Jefe de Auditoría propietario
    del equipo del usuario.

    Para un jefe, retorna el mismo usuario.
    Para un integrante, retorna su administrador.
    """

    if not user or not user.is_authenticated:
        return None

    if is_team_manager(user):
        return user

    owner = getattr(
        user,
        "administrador",
        None,
    )

    if (
        owner
        and is_team_manager(owner)
    ):
        return owner

    return None


def user_is_assigned_to_audit(
    user,
    audit,
):
    """
    Comprueba si el usuario forma parte del equipo
    asignado a la auditoría.
    """

    if not user or not audit:
        return False

    return (
        audit.assigned_users
        .filter(
            id=user.id,
        )
        .exists()
    )


def audit_belongs_to_user_team(
    user,
    audit,
):
    """
    Comprueba que la auditoría pertenece al equipo
    del usuario autenticado.
    """

    owner = get_team_owner(
        user
    )

    if owner is None:
        return False

    return (
        audit.audit_manager_id
        == owner.id
    )


def user_can_access_audit_type(user, audit_type):
    """Habilitaciones comerciales por usuario; Financiera es la base."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff or get_user_role_name(user) == 'superadmin':
        return True
    return {
        'F': True,
        'R': bool(getattr(user, 'revisor_fiscal', False)),
        'I': bool(getattr(user, 'auditoria_interna', False)),
    }.get(audit_type, False)


def allowed_audit_type_codes(user, audit):
    """Intersección de módulos habilitados en el proyecto y en el usuario."""
    return [type_code for type_code in audit.get_active_type_codes()
            if user_can_access_audit_type(user, type_code)]

def user_can_access_audit(
    user,
    audit,
    action="view",
    module="audits",
):
    """
    Control central de acceso a una auditoría.

    Reglas:
    - Superusuario o staff: acceso completo.
    - Jefe: únicamente auditorías propias.
    - Integrante: mismo equipo, estar asignado
      y permiso en la matriz.
    """

    if not user or not user.is_authenticated:
        return False

    # No basta con estar asignado: se necesita un tipo de módulo habilitado.
    if not allowed_audit_type_codes(user, audit):
        return False

    if user.is_superuser or user.is_staff:
        return True

    if is_team_manager(user):
        return (
            audit.audit_manager_id
            == user.id
        )

    role_name = get_user_role_name(
        user
    )

    if role_name not in OPERATIONAL_ROLES:
        return False

    if not audit_belongs_to_user_team(
        user,
        audit,
    ):
        return False

    if not user_is_assigned_to_audit(
        user,
        audit,
    ):
        return False

    return has_module_permission(
        user,
        module,
        action,
    )

def get_audit_for_user_or_404(
    user,
    audit_id,
    action="view",
    module="audits",
):
    """
    Obtiene una auditoría y comprueba el acceso.

    Devuelve 404 para no revelar la existencia
    de auditorías de otros equipos.
    """

    audit = get_object_or_404(
        Audit.objects
        .select_related(
            "audit_manager",
            "audit_manager__role",
        )
        .prefetch_related(
            "assigned_users",
        ),
        pk=audit_id,
    )

    if not user_can_access_audit(
        user,
        audit,
        action=action,
        module=module,
    ):
        raise Http404(
            (
                "La auditoría no existe "
                "o no tienes acceso."
            )
        )

    return audit

