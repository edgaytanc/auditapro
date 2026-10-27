from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)

User = get_user_model()

class Audit(models.Model):
    STATUS_CHOICES = [
        ("planning", "Planificación"),
        ("progress", "En Proceso"),
        ("review", "En Revisión"),
        ("completed", "Finalizada"),
    ]

    RISK_CHOICES = [
        ("undefined", "Sin definir"),
        ("low", "Bajo"),
        ("medium", "Medio"),
        ("high", "Alto"),
    ]
    title = models.CharField(max_length=255)
    fechaInit = models.DateTimeField(default=timezone.now)
    identidad = models.CharField(max_length=255, default='Sin identidad')
    fechaEnd = models.DateTimeField(default=timezone.now)
    tipoAuditoria = models.CharField(max_length=255, default='F')
    moneda = models.CharField(max_length=10, default='GTQ')
    manual_findings_count = models.PositiveIntegerField(
        null=True, blank=True, verbose_name="Número informado de hallazgos",
    )
    progress = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        verbose_name="Avance",
    )

    risk_level = models.CharField(
        max_length=20,
        choices=RISK_CHOICES,
        default="undefined",
        verbose_name="Nivel de riesgo",
    )

    workflow_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name="Estado de la auditoría",
    )
    activa_revisoria = models.BooleanField(default=False, verbose_name="Activar Revisoria")
    activa_financiera = models.BooleanField(
    default=False,
    verbose_name="Activar Auditoría Financiera",
    )

    activa_interna = models.BooleanField(
        default=False,
        verbose_name="Activar Auditoría Interna",
    )

    periodo_auditado = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Período auditado",
    )
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
    
    def get_active_type_codes(self):
        """
        Retorna todos los tipos habilitados en la auditoría.

        Si es una auditoría antigua y todavía no tiene los nuevos
        booleanos configurados, utiliza tipoAuditoria como respaldo.
        """
        selected_types = []

        if self.activa_financiera:
            selected_types.append("F")

        if self.activa_revisoria:
            selected_types.append("R")

        if self.activa_interna:
            selected_types.append("I")

        if not selected_types and self.tipoAuditoria in {
            "F",
            "R",
            "I",
        }:
            selected_types.append(
                self.tipoAuditoria
            )

        return selected_types

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