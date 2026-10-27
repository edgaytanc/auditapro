import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from audits.models import Audit
from audits.utils import audit_to_dict
from users.models import Roles
from users.utils import user_to_dict

from notifications.services import (
    create_notification,
    mark_notification_as_read as mark_notification_as_read_func,
)
from .const import CREATE_NOTIFICATION_ERRORS_INSTANCES
from .models import Notification, NotificationStatus

User = get_user_model()

REJECT_REASONS = [
    "Errores de cálculo",
    "Información incompleta",
    "Falta de evidencia documental",
    "Formato incorrecto",
    "Referencias cruzadas incorrectas",
    "Otros (especificar)",
]


@login_required
def notifications(req):
    if req.method == "GET":
        return notifications_page(req)

    return redirect("notifications")


@login_required
def create_notification_view(req):
    if req.method == "GET":
        return create_notification_page(req)
    if req.method == "POST":
        return push_notification(req)

    return redirect("create_notification")


@login_required
def push_notification(req):
    note = req.POST.get("notification_note")
    audit_id = req.POST.get("audit_id")
    notifieds_ids = req.POST.getlist("notifieds_ids")

    try:
        create_notification(audit_id, notifieds_ids, req.user.id, note)
        messages.success(req, "La notificación fue creada correctamente.")
        return redirect("create_notification")
    except ValueError:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
    except Exception as exc:
        error_message = str(exc)
        if isinstance(exc, CREATE_NOTIFICATION_ERRORS_INSTANCES):
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
    except ValueError:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
    except Exception as exc:
        error_message = str(exc)
        if isinstance(exc, CREATE_NOTIFICATION_ERRORS_INSTANCES):
            messages.error(req, error_message)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )

    return redirect("notifications")


@login_required
def notifications_page(req):
    notifications_qs = (
        NotificationStatus.objects
        .filter(user=req.user)
        .select_related("notification", "notification__audit", "notification__notifier")
        .prefetch_related("notification__audit__assigned_users")
        .order_by("-notification__created_at", "-id")
    )

    filter_value = req.GET.get("filter")
    if filter_value == "readed":
        notifications_qs = notifications_qs.filter(is_read=True)
    elif filter_value == "not_readed":
        notifications_qs = notifications_qs.filter(is_read=False)

    data = {
        "notifications": notifications_qs,
        "motivos_rechazo": REJECT_REASONS,
    }

    return render(req, "notifications/notifications.html", data)


@login_required
def create_notification_page(req):
    notifieds = []
    user_role = getattr(getattr(req.user, "role", None), "name", None)

    auditor_role = Roles.objects.get(name="auditor")

    if user_role == "audit_manager":
        assigned_audits = Audit.objects.filter(audit_manager=req.user).prefetch_related("assigned_users")
    elif user_role == "auditor":
        assigned_audits = Audit.objects.filter(assigned_users=req.user).prefetch_related("assigned_users")
    else:
        assigned_audits = Audit.objects.none()

    if user_role == "audit_manager":
        auditores = (
            User.objects.filter(
                assigned_users__in=assigned_audits,
                role=auditor_role,
            )
            .distinct()
        )
        notifieds.extend(auditores)
    elif user_role == "auditor":
        notifieds.extend(
            audit.audit_manager
            for audit in assigned_audits
            if audit.audit_manager_id
        )

    notifieds_json = json.dumps([user_to_dict(user) for user in notifieds])
    audits_json = json.dumps([audit_to_dict(audit) for audit in assigned_audits])

    data = {
        "notifieds": notifieds,
        "notifieds_json": notifieds_json,
        "audits": assigned_audits,
        "audits_json": audits_json,
    }

    return render(req, "notifications/create-notification.html", data)


@require_POST
@login_required
def review_notification(req, pk):
    notification = get_object_or_404(
        Notification.objects.select_related("audit", "audit__audit_manager"),
        pk=pk,
    )
    audit = notification.audit

    if audit.audit_manager_id != req.user.id:
        raise Http404()

    action = req.POST.get("action")
    reasons = req.POST.getlist("reasons[]")
    comments = (req.POST.get("comments") or "").strip()

    if action not in {"approve", "reject"}:
        return JsonResponse(
            {"ok": False, "error": "Acción de revisión no válida."}, status=400
        )

    if notification.review_status != Notification.REVIEW_STATUS_PENDING:
        return JsonResponse(
            {
                "ok": False,
                "error": "Esta notificación ya fue revisada previamente.",
            },
            status=400,
        )

    if action == "reject" and not reasons and not comments:
        return JsonResponse(
            {
                "ok": False,
                "error": "Para rechazar debes indicar al menos un motivo o comentario.",
            },
            status=400,
        )

    review_status = (
        Notification.REVIEW_STATUS_APPROVED
        if action == "approve"
        else Notification.REVIEW_STATUS_REJECTED
    )

    with transaction.atomic():
        notification.review_status = review_status
        notification.reviewed_by = req.user
        notification.reviewed_at = timezone.now()
        notification.review_meta = {
            "reasons": reasons,
            "comments": comments,
        }
        notification.save(
            update_fields=[
                "review_status",
                "reviewed_by",
                "reviewed_at",
                "review_meta",
            ]
        )

        current_status = NotificationStatus.objects.filter(
            notification=notification,
            user=req.user,
        ).first()
        if current_status and not current_status.is_read:
            current_status.read_notification()

        response_text = (
            "Papel de trabajo APROBADO."
            if action == "approve"
            else (
                "Papel de trabajo RECHAZADO.\n\n"
                f"Motivos: {', '.join(reasons) or '—'}\n"
                f"Comentarios: {comments or '—'}"
            )
        )

        auditor_ids = list(
            audit.assigned_users
            .filter(role__name="auditor")
            .values_list("id", flat=True)
        )

        if auditor_ids:
            create_notification(
                audit.id,
                auditor_ids,
                req.user.id,
                response_text,
            )

    return JsonResponse(
        {
            "ok": True,
            "status": "APROBADO" if action == "approve" else "RECHAZADO",
        }
    )


@login_required
@require_POST
def delete_notification_status(req, ns_id):
    status = get_object_or_404(
        NotificationStatus,
        id=ns_id,
        user=req.user,
    )
    notification = status.notification
    status.delete()

    if not NotificationStatus.objects.filter(notification=notification).exists():
        notification.delete()

    return JsonResponse({"ok": True, "message": "Notificación eliminada."})


@login_required
@require_POST
def delete_notifications(req):
    user = req.user
    user_role = getattr(getattr(user, "role", None), "name", None)

    if user_role == "audit_manager":
        limit_date = timezone.now() - timedelta(days=15)

        old_qs = NotificationStatus.objects.filter(
            user=user,
            is_read=True,
            notification__created_at__lt=limit_date,
        )
        old_count = old_qs.count()
        old_qs.delete()

        duplicate_groups = (
            Notification.objects.values("audit_id", "note")
            .annotate(total=models.Count("id"))
            .filter(total__gt=1)
        )

        duplicates_deleted = 0
        for group in duplicate_groups:
            duplicates = list(
                Notification.objects.filter(
                    audit_id=group["audit_id"],
                    note=group["note"],
                ).order_by("-created_at")[1:]
            )
            for item in duplicates:
                item.delete()
                duplicates_deleted += 1

        message = (
            f"Se limpiaron {old_count} notificaciones antiguas y "
            f"{duplicates_deleted} duplicadas."
        )
    else:
        count = NotificationStatus.objects.filter(user=user).count()
        NotificationStatus.objects.filter(user=user).delete()
        message = f"Se eliminaron tus {count} notificaciones personales."

    return JsonResponse({"ok": True, "message": message})
