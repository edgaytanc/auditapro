from django.http import HttpRequest

from audits.models import Audit
from users.utils import user_to_dict

from .types import Audit as AuditType


def audit_to_dict(
    audit,
) -> AuditType:
    """
    Convierte una auditoría en un diccionario
    que puede guardarse en la sesión.
    """

    return {
        "id": audit.id,
        "title": audit.title,
        "identidad": audit.identidad,
        "fechaInit": (
            audit.fechaInit.isoformat()
        ),
        "fechaEnd": (
            audit.fechaEnd.isoformat()
        ),
        "tipoAuditoria": (
            audit.tipoAuditoria
        ),
        "created_at": (
            audit.created_at.isoformat()
        ),
        "updated_at": (
            audit.updated_at.isoformat()
            if audit.updated_at
            else None
        ),
        "audit_manager": user_to_dict(
            audit.audit_manager
        ),
        "assigned_users": [
            user_to_dict(user)
            for user
            in audit.assigned_users.all()
        ],
    }


def get_assigned_audits(
    user_role: str,
    req: HttpRequest,
):
    """
    Retorna únicamente las auditorías accesibles
    para el usuario autenticado.
    """

    if user_role == "audit_manager":
        return (
            Audit.objects
            .filter(
                audit_manager=req.user,
            )
            .distinct()
        )

    if user_role in {
        "supervisor",
        "auditor",
        "readonly",
    }:
        return (
            Audit.objects
            .filter(
                assigned_users=req.user,
                audit_manager_id=(
                    req.user.administrador_id
                ),
            )
            .distinct()
        )

    return Audit.objects.none()


def get_selected_audit(
    req: HttpRequest,
):
    """
    Selecciona una auditoría después de comprobar
    que el usuario tenga acceso.

    audits.access se importa aquí y no al cargar
    inicialmente el módulo para evitar ciclos.
    """

    from .access import (
        get_audit_for_user_or_404,
    )

    audit_id_selected = req.POST.get(
        "audit"
    )

    selected_audit = (
        get_audit_for_user_or_404(
            req.user,
            audit_id_selected,
            action="view",
        )
    )

    req.session["selected_audit"] = (
        audit_to_dict(
            selected_audit
        )
    )

    return selected_audit