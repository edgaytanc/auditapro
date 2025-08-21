from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()

class Audit(models.Model):
    title = models.CharField(max_length=255)
    fechaInit = models.DateTimeField(default=timezone.now)
    identidad = models.CharField(max_length=255, default='Sin identidad')
    fechaEnd = models.DateTimeField(default=timezone.now)
    tipoAuditoria = models.CharField(max_length=255, default='F')
    moneda = models.CharField(max_length=10, default='GTQ')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    audit_manager = models.ForeignKey(
        User, related_name="audit_manager", on_delete=models.CASCADE
    )
    assigned_users = models.ManyToManyField(
        User, related_name="assigned_users", blank=True
    )

    def __str__(self):
        return f"{self.title} - {self.identidad}"

    def save(self, *args, **kwargs):
        if not self.audit_manager.role.name == "audit_manager":
            raise ValidationError(
                "El usuario asignado como Jefe de Auditoría debe tener el rol de 'audit_manager'."
            )
        if self.fechaEnd < self.fechaInit:
            raise ValidationError(
                "La fecha final debe ser posterior a la fecha de inicio."
            )
        super().save(*args, **kwargs)