from django.db import models
from audits.models import Audit
from django.contrib.auth import get_user_model
from .errors import (
    AuditorInvalidNotifierError,
    SupervisorInvalidNotifierError,
    AuditNotAssignantToUser,
)
from django.utils import timezone

User = get_user_model()


class Notification(models.Model):
    notifier = models.ForeignKey(
        User, related_name="notifier", on_delete=models.CASCADE
    )
    notified_users = models.ManyToManyField(
        User, through="NotificationStatus", related_name="notified_users"
    )

    created_at = models.DateTimeField(default=timezone.now)
    note = models.TextField()
    audit = models.ForeignKey(
        Audit, related_name="notification_audit", on_delete=models.CASCADE
    )

    def check_and_delete_if_done(self):
        if all(notified.is_read == True for notified in self.notified_users.all()):
            self.delete()

    def __str__(self):
        return f"{self.notifier}: {self.note} - {self.created_at}"


class NotificationStatus(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    readed_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.notification.note} - {'Leída' if self.is_read else 'Sin leer'}"

    def read_notification(self):
        self.is_read = True
        self.readed_date = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if (
            self.user not in self.notification.audit.assigned_users.all()
            and self.user.role.name == "auditor"
            or self.user.role.name == "audit_manager"
            and self.user.id != self.notification.audit.audit_manager.id
        ):
            raise AuditNotAssignantToUser(self.user.get_full_name())
        
        # Validar que la comunicación sea solo entre audit_manager y auditor
        if (
            self.notification.notifier.role.name == "auditor"
            and self.user.role.name != "audit_manager"
        ):
            raise AuditorInvalidNotifierError()
        elif (
            self.notification.notifier.role.name == "audit_manager"
            and self.user.role.name != "auditor"
        ):
            raise SupervisorInvalidNotifierError()
            
        super().save(*args, **kwargs)
