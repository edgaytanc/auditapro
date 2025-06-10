import json
from django.forms import model_to_dict
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from audits.models import Audit
from users.utils import user_to_dict
from .types import Audit as AuditType


def audit_to_dict(audit) -> AuditType:
    return {
        "id": audit.id,
        "title": audit.title,
        "identidad": audit.identidad,
        "fechaInit": audit.fechaInit.isoformat(),
        "fechaEnd": audit.fechaEnd.isoformat(),
        "tipoAuditoria": audit.tipoAuditoria,
        "created_at": audit.created_at.isoformat(),
        "updated_at": audit.updated_at.isoformat() if audit.updated_at else None,
        "audit_manager": user_to_dict(audit.audit_manager),
        "assigned_users": [user_to_dict(user) for user in audit.assigned_users.all()],
    }


def get_assigned_audits(user_role: str, req: HttpRequest):
    if user_role == "audit_manager":
        return Audit.objects.filter(audit_manager=req.user)
    elif user_role in ["supervisor", "auditor"]:
        return Audit.objects.filter(assigned_users=req.user)


def get_selected_audit(req: HttpRequest):
    audit_id_selected = req.POST.get("audit")
    user_role = req.user.role.name
    if user_role == "audit_manager":
        selected_audit = get_object_or_404(
            Audit, audit_manager=req.user, pk=audit_id_selected
        )
    elif user_role in ["supervisor", "auditor"]:
        selected_audit = get_object_or_404(
            Audit, assigned_users=req.user, pk=audit_id_selected
        )

    # Serializar el diccionario en JSON
    req.session["selected_audit"] = audit_to_dict(selected_audit)

    return selected_audit
