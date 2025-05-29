from audits.models import Audit
from django.contrib.auth import get_user_model
from .models import Notification, NotificationStatus
from audits.errors import AuditDoNotExits, AuditsNullError
from notifications.errors import (
    InvalidNotifiedsNotificationError,
    InvalidNotifierError,
    NotifierDoNotExits,
    InvalidNoteNotificationError,
    NotifiedsNotificatonDoNotExitsError,
    NotificationDoNotExits,
)

from users.errors import UserDoNotExits, UserUnauthorized

User = get_user_model()


def create_multiple_notification_status(
    notification,
    notifieds_ids: list[str],
):
    try:
        if not notifieds_ids:
            raise InvalidNotifiedsNotificationError()

        if not notification:
            raise NotificationDoNotExits()

        for id in notifieds_ids:
            user_to_notify = User.objects.get(id=id)

            if not user_to_notify:
                raise NotifiedsNotificatonDoNotExitsError(id)

            NotificationStatus.objects.create(
                notification=notification, user=user_to_notify
            )
    except Exception as e:
        raise e


def create_notification_status(notification_id, notifier_id):
    try:
        notification = Notification.objects.get(id=notification_id)
        if not notification:
            raise NotificationDoNotExits()
        user = User.objects.get(id=notifier_id)
        if not user:
            raise NotifiedsNotificatonDoNotExitsError(notifier_id)

        NotificationStatus.objects.create(notification=notification, user=user)
    except Exception as e:
        raise e


def create_notification(audit_id, notifieds_ids, notifier_id, notification_note):
    new_notification = None
    try:
        if not audit_id:
            raise AuditsNullError()
        if not notifieds_ids:
            raise InvalidNotifiedsNotificationError()
        if not notifier_id:
            raise InvalidNotifierError()
        if not notification_note:
            raise InvalidNoteNotificationError()

        notifier = User.objects.get(id=notifier_id)
        if not notifier:
            raise NotifierDoNotExits()

        related_audit = Audit.objects.get(id=audit_id)
        if not related_audit:
            raise AuditDoNotExits()

        new_notification = Notification.objects.create(
            notifier=notifier, audit=related_audit, note=notification_note
        )

        if isinstance(notifieds_ids, list):
            create_multiple_notification_status(new_notification, notifieds_ids)
        else:
            create_notification_status(new_notification, notifieds_ids)
    except Exception as e:
        if new_notification:
            new_notification.delete()
        raise e


def mark_notification_as_read(user, notification_status_id: int):
    try:
        if not user:
            raise UserDoNotExits()
        if not notification_status_id:
            raise NotificationDoNotExits()
        notification_status_to_read = NotificationStatus.objects.get(
            id=notification_status_id
        )
        if not notification_status_to_read:
            raise NotificationDoNotExits()
        if notification_status_to_read.user.id != user.id:
            raise UserUnauthorized()

        notification_status_to_read.read_notification()
        notification_status_to_read.save()
    except NotificationStatus.DoesNotExist as e:
        raise NotificationDoNotExits()
    except Exception as e:
        raise e
