from django.conf import settings
from django.db import models
from django.utils import timezone
import datetime

class TwoFactorAuth(models.Model):
    """
    Almacena los códigos de autenticación de dos factores (2FA) para los usuarios.

    Atributos:
        user (ForeignKey): La relación con el usuario al que pertenece el código.
        code (CharField): El código de 6 dígitos generado.
        created_at (DateTimeField): La fecha y hora de creación del código.
        expires_at (DateTimeField): La fecha y hora en que el código expira (5 minutos por defecto).
        is_used (BooleanField): Indica si el código ya ha sido utilizado.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='two_factor_codes',
        verbose_name="Usuario"
    )
    code = models.CharField(
        max_length=6,
        verbose_name="Código de Verificación"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    expires_at = models.DateTimeField(
        verbose_name="Fecha de Expiración"
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="¿Fue usado?"
    )

    def is_expired(self):
        """
        Verifica si el código ha expirado.

        Returns:
            bool: True si la fecha y hora actual es posterior a la de expiración.
        """
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save para establecer la fecha de expiración
        automáticamente al crear un nuevo código.
        """
        if not self.id:  # Se ejecuta solo al crear el objeto.
            # El código será válido por 5 minutos.
            self.expires_at = timezone.now() + datetime.timedelta(minutes=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Código 2FA para {self.user.email}"

    class Meta:
        verbose_name = "Código de Autenticación de Dos Factores"
        verbose_name_plural = "Códigos de Autenticación de Dos Factores"
        ordering = ['-created_at']

