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
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
from users.models import User  # asegúrate que apunte al modelo correcto
from django.db import models


from .models import Notification  # ajusta al nombre real del modelo

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

    # ✅ Agregar motivos de rechazo (se usan en los modales)
    data["motivos_rechazo"] = [
        "Errores de cálculo",
        "Información incompleta",
        "Falta de evidencia documental",
        "Formato incorrecto",
        "Referencias cruzadas incorrectas",
        "Otros (especificar)"
    ]

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


@login_required
def notification_detail(request, pk):
    notif = get_object_or_404(Notification, pk=pk)
    audit = getattr(notif, "audit", None)
    is_supervisor = bool(audit and audit.audit_manager_id == request.user.id)

    ctx = {
        "notif": notif,
        "is_supervisor": is_supervisor,
        "reject_reasons": [
            "Errores de cálculo",
            "Información incompleta",
            "Falta de evidencia documental",
            "Formato incorrecto",
            "Referencias cruzadas incorrectas",
            "Otros (especificar)",
        ],
        "motivos_rechazo": [
            "Errores de cálculo",
            "Información incompleta",
            "Falta de evidencia documental",
            "Formato incorrecto",
            "Referencias cruzadas incorrectas",
            "Otros (especificar)",
        ],
    }
    return render(request, "notifications/notification_detail.html", ctx)




@require_POST
@login_required
def review_notification(request, pk):
    print(f"\n--- [DEBUG] review_notification ---")
    print(f"User: {request.user}")
    print(f"PK: {pk}")
    print(f"POST: {request.POST}")

    try:
        notif = Notification.objects.get(pk=pk)
        audit = getattr(notif, "audit", None)
        print(f"Audit: {audit}")

        # Seguridad: solo el jefe de auditoría puede revisar
        if not audit or audit.audit_manager_id != request.user.id:
            print("[ERROR] Usuario no autorizado o auditoría inválida")
            raise Http404()

        # 🚫 Evitar reenvíos o revisiones duplicadas
        if hasattr(notif, "reviewed_at") and notif.reviewed_at:
            return JsonResponse({
                "ok": False,
                "error": "Esta auditoría ya fue revisada previamente."
            }, status=400)

        action = request.POST.get("action")
        reasons = request.POST.getlist("reasons[]", [])
        comments = (request.POST.get("comments") or "").strip()
        print(f"Action: {action}, Reasons: {reasons}, Comments: {comments}")

        # ✅ Marca como leída si el modelo lo permite
        if hasattr(notif, "is_read"):
            notif.is_read = True

        # ✅ Guarda fecha de revisión y comentarios
        if hasattr(notif, "reviewed_by"):
            notif.reviewed_by = request.user
        if hasattr(notif, "reviewed_at"):
            notif.reviewed_at = timezone.now()
        if hasattr(notif, "review_meta"):
            notif.review_meta = {"reasons": reasons, "comments": comments}

        notif.save()
        print("[OK] Notificación actualizada correctamente")

        # ✅ Crear notificación de respuesta para los auditores asignados
        try:
            msg = (
                "✅ Papel de trabajo APROBADO."
                if action == "approve"
                else f"❌ Papel de trabajo RECHAZADO.\n\nMotivos: {', '.join(reasons) or '—'}\nComentarios: {comments or '—'}"
            )

            notif_fields = [f.name for f in Notification._meta.fields]
            create_kwargs = {"audit": audit, "note": msg}

            if "notifier" in notif_fields:
                create_kwargs["notifier"] = request.user

            # 📨 Crear la notificación base
            response_notif = Notification.objects.create(**create_kwargs)
            print("[OK] Notificación de respuesta creada")

            # 🧍‍♂️ Crear NotificationStatus para auditores únicos
            assigned_auditors = list(set(audit.assigned_users.values_list("id", flat=True)))
            print(f"[INFO] Auditores únicos detectados: {assigned_auditors}")

            for auditor_id in assigned_auditors:
                auditor = User.objects.filter(id=auditor_id).first()
                if not auditor:
                    print(f"[WARN] Auditor con id {auditor_id} no encontrado")
                    continue

                # Evitar duplicados en BD
                if NotificationStatus.objects.filter(
                    user=auditor, notification=response_notif
                ).exists():
                    print(f"[SKIP] Ya existe notificación para {auditor}")
                    continue

                NotificationStatus.objects.create(
                    user=auditor,
                    notification=response_notif,
                    is_read=False
                )
                print(f"[OK] Notificación enviada a: {auditor}")

        except Exception as e:
            print(f"[WARN] No se pudo crear notificación de respuesta: {e}")

        # 🔚 Limpieza automática (opcional)
        clean_old_notifications(days=15)

        # 🔚 Respuesta al frontend
        status_text = "APROBADO" if action == "approve" else "RECHAZADO"
        return JsonResponse({"ok": True, "status": status_text})

    except Exception as e:
        print(f"[ERROR] review_notification fallo: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# 🧹 Utilidad para limpiar notificaciones viejas o duplicadas
def clean_old_notifications(days: int = 30):
    """
    Elimina notificaciones con más de 'days' días de antigüedad
    o notificaciones duplicadas (mismo texto y auditoría).
    """
    try:
        limit_date = timezone.now() - timedelta(days=days)

        # 1️⃣ Borrar notificaciones viejas
        old_qs = Notification.objects.filter(created_at__lt=limit_date)
        deleted_old, _ = old_qs.delete()
        print(f"[CLEANUP] Notificaciones antiguas eliminadas: {deleted_old}")

        # 2️⃣ Borrar duplicados (mismo audit y note)
        duplicates = (
            Notification.objects
            .values("audit_id", "note")
            .annotate(total=models.Count("id"))
            .filter(total__gt=1)
        )

        for dup in duplicates:
            dups_to_delete = (
                Notification.objects.filter(
                    audit_id=dup["audit_id"], note=dup["note"]
                ).order_by("-created_at")[1:]
            )
            count = dups_to_delete.count()
            dups_to_delete.delete()
            if count:
                print(f"[CLEANUP] Eliminadas {count} duplicadas en auditoría {dup['audit_id']}")

    except Exception as e:
        print(f"[WARN] Error durante la limpieza de notificaciones: {e}")
        
        
from django.db import models, transaction

@login_required
def delete_notifications(request):
    """
    Permite eliminar notificaciones:
    - El jefe de auditoría limpia duplicadas, viejas y estados huérfanos.
    - El auditor elimina solo sus notificaciones personales.
    """
    try:
        user = request.user

        # 🔒 Anti-reentrancia simple por sesión (evita doble POST solapado)
        if request.session.get("notif_cleanup_in_progress"):
            print("[CLEANUP] Ignorado: limpieza YA en curso para este usuario.")
            return JsonResponse({"ok": True, "message": "Limpieza ya en curso…"})

        request.session["notif_cleanup_in_progress"] = True
        request.session.modified = True

        try:
            print(f"[CLEANUP] >>> Inicio por {user} (rol={getattr(user.role,'name',None)})")

            # ============================================================
            # 🔹 JEFE DE AUDITORÍA
            # ============================================================
            if user.role.name == "audit_manager":
                limit_date = timezone.now() - timedelta(days=15)

                # 1️⃣ Eliminar notificaciones antiguas (leídas y >15 días)
                old_qs = NotificationStatus.objects.filter(
                    is_read=True,
                    notification__created_at__lt=limit_date
                )
                count_old = old_qs.count()
                old_qs.delete()

                # 2️⃣ Eliminar duplicadas por (audit_id, note)
                duplicates = (
                    Notification.objects
                    .values("audit_id", "note")
                    .annotate(total=models.Count("id"))
                    .filter(total__gt=1)
                )

                deleted_dups = 0
                for dup in duplicates:
                    dups_qs = Notification.objects.filter(
                        audit_id=dup["audit_id"],
                        note=dup["note"]
                    ).order_by("-created_at")

                    # Mantener el más reciente y borrar el resto
                    to_delete = list(dups_qs[1:])
                    deleted_dups += len(to_delete)

                    # Borrar uno-a-uno para evitar error con slicing
                    for notif in to_delete:
                        notif.delete()

                # 3️⃣ Eliminar estados huérfanos (sin Notification asociada)
                orphan_qs = NotificationStatus.objects.filter(notification__isnull=True)
                count_orphan = orphan_qs.count()
                orphan_qs.delete()

                # 🧾 Mensaje resumen
                msg = (
                    f"🧹 Se eliminaron {count_old} antiguas, "
                    f"{deleted_dups} duplicadas y {count_orphan} estados huérfanos."
                )

                print(f"[CLEANUP] Eliminadas: antiguas={count_old}, duplicadas={deleted_dups}, huérfanas={count_orphan}")

            # ============================================================
            # 🔹 AUDITOR
            # ============================================================
            else:
                personal_qs = NotificationStatus.objects.filter(user=user)
                count_personal = personal_qs.count()
                personal_qs.delete()

                msg = f"🗑️ Se eliminaron tus {count_personal} notificaciones personales."
                print(f"[CLEANUP] Eliminadas personales={count_personal}")

            # ✅ Respuesta final
            return JsonResponse({"ok": True, "message": msg})

        finally:
            # liberar el lock de sesión
            request.session["notif_cleanup_in_progress"] = False
            request.session.modified = True

    except Exception as e:
        print(f"[ERROR] delete_notifications: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# 👇 NUEVO: eliminar una sola notificación del auditor
from django.views.decorators.http import require_POST

@require_POST
@login_required
def delete_notification_status(request, ns_id: int):
    """
    El auditor elimina SOLO su NotificationStatus (una tarjeta).
    Si ese NotificationStatus era el último para la Notification base,
    se elimina también la Notification huérfana (opcional, seguro).
    """
    try:
        # Asegura que pertenece al usuario actual
        ns = get_object_or_404(NotificationStatus, id=ns_id, user=request.user)

        notif = ns.notification  # guarda referencia antes de borrar
        ns.delete()

        # (Opcional seguro) Si ya no hay estados vinculados, borra la Notification base
        if not NotificationStatus.objects.filter(notification=notif).exists():
            notif.delete()

        return JsonResponse({"ok": True, "message": "Notificación eliminada."})
    except Http404:
        return JsonResponse({"ok": False, "error": "No encontrada."}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
