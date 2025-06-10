from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from users.models import Roles
from .models import NotificationStatus
from django.core.serializers import serialize
from django.contrib.auth import get_user_model
from audits.models import Audit
from notifications.services import (
    create_notification,
    mark_notification_as_read as mark_notification_as_read_func,
)
from .const import CREATE_NOTIFICATION_ERRORS_INSTANCES
import json
from users.utils import user_to_dict
from audits.utils import audit_to_dict

User = get_user_model()


@login_required
def notifications(req):
    if req.method == "GET":
        return notifications_page(req)


@login_required
def create_notification_view(req):
    if req.method == "GET":
        return create_notification_page(req)
    elif req.method == "POST":
        return push_notification(req)


@login_required
def push_notification(req):
    note = req.POST.get("notification_note")
    audit_id = req.POST.get("audit_id")
    notifieds_ids = req.POST.getlist("notifieds_ids")

    try:
        create_notification(audit_id, notifieds_ids, req.user.id, note)
        messages.success(req, "La notificación fue creada correctamente.")
        return redirect("create_notification")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_notification")
    except Exception as e:
        error_message = str(e)
        if isinstance(e, CREATE_NOTIFICATION_ERRORS_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
        return redirect("create_notification")


@login_required
def mark_notification_as_read(req, notification_status_id):
    try:
        mark_notification_as_read_func(req.user, notification_status_id)
        return redirect("notifications")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("notifications")
    except Exception as e:
        error_message = str(e)
        if isinstance(e, CREATE_NOTIFICATION_ERRORS_INSTANCES):
            messages.error(req, error_message)
            return redirect("notifications")

        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )

            return redirect("notifications")


@login_required
def notifications_page(req):
    notifications = NotificationStatus.objects.filter(user=req.user)
    data = {"notifications": notifications}

    if filter == "readed":
        filter_notifications = notifications.filter(is_read=True)
        data["notifications"] = filter_notifications
    elif filter == "not_readed":
        filter_notifications = notifications.filter(is_read=False)
        data["notifications"] = filter_notifications

    return render(req, "notifications/notifications.html", data)


@login_required
def create_notification_page(req):
    notifieds = []
    user_role = req.user.role.name
    
    # Solo necesitamos el rol de auditor
    auditor_role = Roles.objects.get(name="auditor")
    audit_manager_role = Roles.objects.get(name="audit_manager")
    
    # Obtener auditorías según el rol
    if user_role == "audit_manager":
        assigned_audits = Audit.objects.filter(audit_manager=req.user)
    elif user_role == "auditor":
        assigned_audits = Audit.objects.filter(assigned_users=req.user)
    else:
        # Para cualquier otro rol, no hay auditorías asignadas
        assigned_audits = Audit.objects.none()

    # Determinar a quién puede notificar según el rol
    if user_role == "audit_manager":
        # Jefe de auditoría puede notificar a auditores
        auditores = User.objects.filter(
            assigned_users__in=assigned_audits, role=auditor_role
        ).distinct()
        notifieds.extend(auditores)
        
    elif user_role == "auditor":
        # Auditores pueden notificar a jefes de auditoría
        audit_managers = [audit.audit_manager for audit in assigned_audits]
        notifieds.extend(audit_managers)
    
    # Convertir a JSON para la plantilla
    notifieds_json = json.dumps([user_to_dict(user) for user in notifieds])
    audits_json = json.dumps([audit_to_dict(audit) for audit in assigned_audits])

    data = {
        "notifieds": notifieds,
        "notifieds_json": notifieds_json,
        "audits": assigned_audits,
        "audits_json": audits_json,
    }

    return render(req, "notifications/create-notification.html", data)
