from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from audits.models import Audit


class PermanentFileEntry(models.Model):
    """
    Registro individual del Archivo Permanente.

    El campo `data` permite manejar filas con estructuras
    diferentes, por ejemplo:

    Información general:
        {
            "campo": "Dirección",
            "valor": "..."
        }

    Cuenta bancaria:
        {
            "banco": "...",
            "numero_cuenta": "...",
            "tipo": "...",
            "saldo": "...",
            "moneda": "..."
        }
    """

    SECTION_CHOICES = [
        (
            "general",
            "1. Información General",
        ),
        (
            "organization",
            "2. Estructura Organizacional",
        ),
        (
            "regulations",
            "3. Leyes y Regulaciones",
        ),
        (
            "operations",
            "4. Planificación de Operaciones",
        ),
        (
            "administrative",
            "5. Información Administrativa",
        ),
        (
            "financial",
            (
                "6. Información Contable, "
                "Presupuestaria y Financiera"
            ),
        ),
    ]

    ORIGIN_CHOICES = [
        (
            "automatic",
            "Automático",
        ),
        (
            "manual",
            "Manual",
        ),
    ]

    audit = models.ForeignKey(
        Audit,
        on_delete=models.CASCADE,
        related_name="permanent_file_entries",
        verbose_name="Auditoría",
    )

    section = models.CharField(
        max_length=30,
        choices=SECTION_CHOICES,
        verbose_name="Sección",
    )

    group_key = models.CharField(
        max_length=80,
        verbose_name="Grupo",
        help_text=(
            "Identifica la tabla o bloque dentro "
            "de la sección."
        ),
    )

    row_key = models.CharField(
        max_length=120,
        verbose_name="Identificador de fila",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="Título o campo",
    )

    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Datos",
    )

    origin = models.CharField(
        max_length=20,
        choices=ORIGIN_CHOICES,
        default="manual",
        verbose_name="Origen",
    )

    guide = models.TextField(
        blank=True,
        default="",
        verbose_name="Guía para el auditor",
    )

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Orden",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            "permanent_file_entries_created"
        ),
        null=True,
        blank=True,
        verbose_name="Creado por",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name=(
            "permanent_file_entries_updated"
        ),
        null=True,
        blank=True,
        verbose_name="Actualizado por",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    class Meta:
        verbose_name = (
            "Registro del Archivo Permanente"
        )

        verbose_name_plural = (
            "Registros del Archivo Permanente"
        )

        ordering = [
            "section",
            "group_key",
            "sort_order",
            "id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "audit",
                    "section",
                    "row_key",
                ],
                name="unique_perm_entry_per_audit",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "audit",
                    "section",
                ],
                name="perm_audit_section_idx",
            ),
            models.Index(
                fields=[
                    "section",
                    "is_active",
                ],
                name="perm_section_active_idx",
            ),
        ]

    def clean(self):
        """
        Comprueba que `data` sea un objeto JSON
        con pares clave-valor.
        """

        if not isinstance(
            self.data,
            dict,
        ):
            raise ValidationError({
                "data": (
                    "Los datos del registro deben "
                    "tener formato de objeto."
                ),
            })

    def __str__(self):
        return (
            f"{self.get_section_display()} "
            f"- {self.title}"
        )