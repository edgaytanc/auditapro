from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

from audits.models import Audit


class InternalAuditPlan(models.Model):
    """
    Planificación principal de una Auditoría Interna.
    """

    audit = models.OneToOneField(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_plan",
        verbose_name="Auditoría",
    )

    client_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Nombre de cuenta o cliente",
    )

    objective = models.TextField(
        blank=True,
        default="",
        verbose_name="Objetivo",
    )

    scope = models.TextField(
        blank=True,
        default="",
        verbose_name="Alcance",
    )

    methodology = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Metodología",
    )

    budgeted_hours = models.PositiveIntegerField(
        default=0,
        verbose_name="Horas presupuestadas",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de inicio",
    )

    estimated_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de cierre estimada",
    )

    assigned_team = models.TextField(
        blank=True,
        default="",
        verbose_name="Equipo asignado",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_plans_created",
        verbose_name="Creado por",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_plans_updated",
        verbose_name="Actualizado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Planificación de Auditoría Interna"
        verbose_name_plural = (
            "Planificaciones de Auditoría Interna"
        )

    def clean(self):
        if (
            self.start_date
            and self.estimated_end_date
            and self.estimated_end_date
            < self.start_date
        ):
            raise ValidationError({
                "estimated_end_date": (
                    "La fecha de cierre debe ser "
                    "posterior a la fecha de inicio."
                ),
            })

    def __str__(self):
        return f"Plan interno - {self.audit.title}"


class InternalAuditRisk(models.Model):
    """
    Riesgo evaluado por proceso.

    Riesgo inherente:
        probabilidad × impacto.

    Riesgo residual:
        riesgo inherente ×
        (1 - factor de reducción del control).
    """

    CONTROL_CHOICES = [
        ("adequate", "Adecuado"),
        ("partial", "Parcial"),
        ("none", "No existe"),
    ]

    CONTROL_REDUCTION = {
        "adequate": 0.55,
        "partial": 0.25,
        "none": 0.00,
    }

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_risks",
        verbose_name="Auditoría",
    )

    process = models.CharField(
        max_length=255,
        verbose_name="Proceso",
    )

    risk = models.TextField(
        verbose_name="Riesgo",
    )

    probability = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name="Probabilidad",
    )

    impact = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        verbose_name="Impacto",
    )

    control_level = models.CharField(
        max_length=20,
        choices=CONTROL_CHOICES,
        default="none",
        verbose_name="Control existente",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_risks_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_risks_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Riesgo de Auditoría Interna"
        verbose_name_plural = (
            "Riesgos de Auditoría Interna"
        )
        ordering = [
            "sort_order",
            "id",
        ]
        indexes = [
            models.Index(
                fields=[
                    "audit",
                    "control_level",
                ],
                name="int_risk_audit_ctrl_idx",
            ),
        ]

    @property
    def inherent_score(self):
        return self.probability * self.impact

    @property
    def residual_score(self):
        reduction = self.CONTROL_REDUCTION.get(
            self.control_level,
            0,
        )

        return round(
            self.inherent_score
            * (1 - reduction),
            2,
        )

    @staticmethod
    def classify_score(score):
        if score >= 15:
            return "high"

        if score >= 8:
            return "medium"

        return "low"

    @property
    def inherent_level(self):
        return self.classify_score(
            self.inherent_score
        )

    @property
    def residual_level(self):
        return self.classify_score(
            self.residual_score
        )

    def __str__(self):
        return f"{self.process} - {self.audit.title}"


class InternalAuditControl(models.Model):
    """
    Evaluación del diseño y funcionamiento
    de un control interno.
    """

    TYPE_CHOICES = [
        ("preventive", "Preventivo"),
        ("detective", "Detectivo"),
        ("corrective", "Correctivo"),
    ]

    DESIGN_CHOICES = [
        ("adequate", "Adecuado"),
        ("not_adequate", "No adecuado"),
    ]

    OPERATION_CHOICES = [
        ("effective", "Efectivo"),
        ("not_effective", "No efectivo"),
    ]

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_controls",
        verbose_name="Auditoría",
    )

    risk = models.ForeignKey(
        InternalAuditRisk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="controls",
        verbose_name="Riesgo relacionado",
    )

    control = models.TextField(
        verbose_name="Control",
    )

    control_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="preventive",
        verbose_name="Tipo",
    )

    design = models.CharField(
        max_length=20,
        choices=DESIGN_CHOICES,
        default="adequate",
        verbose_name="Diseño",
    )

    operation = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
        default="effective",
        verbose_name="Operación",
    )

    conclusion = models.TextField(
        blank=True,
        default="",
        verbose_name="Conclusión",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_controls_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_controls_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Control de Auditoría Interna"
        verbose_name_plural = (
            "Controles de Auditoría Interna"
        )
        ordering = [
            "sort_order",
            "id",
        ]
        indexes = [
            models.Index(
                fields=[
                    "audit",
                    "control_type",
                ],
                name="int_ctrl_audit_type_idx",
            ),
        ]

    @property
    def effectiveness_level(self):
        if (
            self.design == "adequate"
            and self.operation == "effective"
        ):
            return "adequate"

        if (
            self.design == "adequate"
            or self.operation == "effective"
        ):
            return "partial"

        return "none"

    def clean(self):
        if (
            self.risk_id
            and self.risk.audit_id
            != self.audit_id
        ):
            raise ValidationError({
                "risk": (
                    "El riesgo debe pertenecer "
                    "a la misma auditoría."
                ),
            })

    def __str__(self):
        return f"{self.control[:60]} - {self.audit.title}"


class InternalAuditFinding(models.Model):
    """
    Hallazgo, recomendación y seguimiento
    del plan de acción.
    """

    SEVERITY_CHOICES = [
        ("significant", "Significativo"),
        ("moderate", "Moderado"),
        ("minor", "Leve"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pendiente"),
        ("in_progress", "En proceso"),
        ("implemented", "Implementado"),
    ]

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_findings",
        verbose_name="Auditoría",
    )

    code = models.CharField(
        max_length=30,
        verbose_name="ID",
    )

    finding = models.TextField(
        verbose_name="Hallazgo",
    )

    process = models.CharField(
        max_length=255,
        verbose_name="Proceso",
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="moderate",
        verbose_name="Severidad",
    )

    recommendation = models.TextField(
        blank=True,
        default="",
        verbose_name="Recomendación",
    )

    responsible = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Responsable",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="Estado",
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de seguimiento",
    )

    corrective_action = models.TextField(
        blank=True,
        default="",
        verbose_name="Acción correctiva",
    )

    action_progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
        verbose_name="Avance",
    )

    evidence = models.TextField(
        blank=True,
        default="",
        verbose_name="Evidencia",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_findings_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_findings_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Hallazgo de Auditoría Interna"
        verbose_name_plural = (
            "Hallazgos de Auditoría Interna"
        )
        ordering = [
            "sort_order",
            "code",
            "id",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "audit",
                    "code",
                ],
                name="unique_internal_finding_code",
            ),
        ]
        indexes = [
            models.Index(
                fields=[
                    "audit",
                    "severity",
                    "status",
                ],
                name="int_find_aud_sev_st_idx",
            ),
        ]

    @property
    def days_to_follow_up(self):
        if self.follow_up_date is None:
            return None

        return (
            self.follow_up_date
            - date.today()
        ).days

    @property
    def deadline_level(self):
        days = self.days_to_follow_up

        if days is None:
            return "undefined"

        if days < 0:
            return "overdue"

        if days <= 7:
            return "urgent"

        if days <= 15:
            return "soon"

        return "normal"

    def __str__(self):
        return f"{self.code} - {self.audit.title}"


class InternalAuditSchedulePhase(models.Model):
    """
    Fase del Cronograma de Auditoría Interna.

    Estado y avance se calculan a partir de las fechas.
    """

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_schedule_phases",
        verbose_name="Auditoría",
    )

    phase = models.CharField(
        max_length=255,
        verbose_name="Fase",
    )

    start_date = models.DateField(
        verbose_name="Fecha de inicio",
    )

    end_date = models.DateField(
        verbose_name="Fecha de finalización",
    )

    responsible = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Responsable",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_schedule_phases_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_schedule_phases_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Fase de Auditoría Interna"
        verbose_name_plural = (
            "Fases de Auditoría Interna"
        )
        ordering = [
            "sort_order",
            "start_date",
            "id",
        ]
        indexes = [
            models.Index(
                fields=[
                    "audit",
                    "start_date",
                    "end_date",
                ],
                name="int_phase_audit_date_idx",
            ),
        ]

    def clean(self):
        if (
            self.start_date
            and self.end_date
            and self.end_date
            < self.start_date
        ):
            raise ValidationError({
                "end_date": (
                    "La fecha final debe ser "
                    "posterior a la fecha de inicio."
                ),
            })

    @property
    def calculated_status(self):
        today = date.today()

        if today < self.start_date:
            return "pending"

        if today > self.end_date:
            return "completed"

        return "in_progress"

    @property
    def calculated_progress(self):
        status = self.calculated_status

        if status == "pending":
            return 0

        if status == "completed":
            return 100

        duration = (
            self.end_date
            - self.start_date
        ).days

        if duration <= 0:
            return 100

        elapsed = (
            date.today()
            - self.start_date
        ).days

        return max(
            0,
            min(
                100,
                round(
                    elapsed
                    / duration
                    * 100
                ),
            ),
        )

    def __str__(self):
        return f"{self.phase} - {self.audit.title}"


def default_report_sections():
    return [
        "cover",
        "executive_summary",
        "objective_scope",
        "methodology",
        "risk_matrix",
        "findings",
        "action_plan",
        "schedule",
        "conclusion",
    ]


class InternalAuditReport(models.Model):
    """
    Configuración y datos manuales del Informe Final.
    """

    audit = models.OneToOneField(
        Audit,
        on_delete=models.CASCADE,
        related_name="internal_report",
        verbose_name="Auditoría",
    )

    enabled_sections = models.JSONField(
        default=default_report_sections,
        verbose_name="Secciones activas",
    )

    executive_summary = models.TextField(
        blank=True,
        default="",
        verbose_name="Resumen ejecutivo",
    )

    conclusion = models.TextField(
        blank=True,
        default="",
        verbose_name="Conclusión",
    )

    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_reports_prepared",
        verbose_name="Preparado por",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="internal_reports_reviewed",
        verbose_name="Revisado por",
    )

    issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de emisión",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Informe de Auditoría Interna"
        verbose_name_plural = (
            "Informes de Auditoría Interna"
        )

    def clean(self):
        if not isinstance(
            self.enabled_sections,
            list,
        ):
            raise ValidationError({
                "enabled_sections": (
                    "Las secciones activas deben "
                    "guardarse como una lista."
                ),
            })

    def __str__(self):
        return f"Informe interno - {self.audit.title}"

class InternalAuditListOverride(models.Model):
    """Datos editables de la ficha/listado, sin alterar el encargo original.

    Las automatizaciones del encargo continúan usando Audit y el cronograma.
    """
    audit = models.OneToOneField(
        Audit, on_delete=models.CASCADE,
        related_name="internal_list_override",
    )
    display_code = models.CharField(max_length=60, blank=True, default="")
    process_area = models.CharField(max_length=255, blank=True, default="")
    client = models.CharField(max_length=255, blank=True, default="")
    auditor_name = models.CharField(max_length=255, blank=True, default="")
    manual_progress = models.PositiveSmallIntegerField(null=True, blank=True)
    manual_close_date = models.DateField(null=True, blank=True)
    manual_status = models.CharField(max_length=20, blank=True, default="")
    manual_risk = models.CharField(max_length=20, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Resumen manual · {self.audit_id}"
