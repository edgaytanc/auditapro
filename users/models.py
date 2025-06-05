from typing import Iterable
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class Roles(models.Model):
    name = models.CharField(max_length=255)
    verbose_name = models.CharField(max_length=255)

    def __str__(self):
        return self.verbose_name


def get_default_role():
    role, _ = Roles.objects.get_or_create(name="auditor", verbose_name="Auditor")
    return role


class User(AbstractUser):
    MODALIDAD_CHOICES = [
        ('I', 'Modalidad Individual'),
        ('G', 'Modalidad Grupal'),
    ]
    
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    signature = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Campo para identificar la modalidad (individual o grupal)
    modalidad = models.CharField(
        max_length=1,
        choices=MODALIDAD_CHOICES,
        default='I',
        help_text="Indica si el usuario pertenece a modalidad individual (I) o grupal (G)"
    )
    
    # Campo para identificar el plan específico (letra)
    plan = models.CharField(
        max_length=1,
        default='M',
        help_text="Letra que identifica el plan específico (M: mensual, etc.)"
    )
    
    # Relación con el administrador (para usuarios en modalidad grupal)
    administrador = models.ForeignKey(
        'self',
        related_name='auditores',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Administrador al que está asociado este usuario (para modalidad grupal)"
    )

    role = models.ForeignKey(
        Roles,
        related_name="role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self) -> str:
        return f"{self.username}"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.role:  # Si no se ha asignado un rol
            self.role = get_default_role()  # Asignamos el rol por defecto
        super().save(*args, **kwargs)
    
    def is_admin(self):
        """Verifica si el usuario es un administrador."""
        return self.role.name == "audit_manager"
    
    def get_auditores(self):
        """Obtiene todos los auditores asociados a este administrador."""
        if not self.is_admin():
            return User.objects.none()
        
        return self.auditores.all()
