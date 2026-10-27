from django.conf import settings
from django.db import models


class CupoConsultasIA(models.Model):
    """Contadores por usuario (PK), NO guarda preguntas, respuestas ni archivos."""

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cupo_audita_analisis",
    )
    restantes = models.PositiveIntegerField(default=5)
    realizadas = models.PositiveIntegerField(default=0)
    version_cupo = models.PositiveIntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cupo de Audita Análisis"
        verbose_name_plural = "Cupos de Audita Análisis"

    def __str__(self):
        return f"{self.usuario_id} · {self.restantes} consultas disponibles"
