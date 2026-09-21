from typing import Iterable
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone



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
        ('S', 'Superadmin'),
    ]

    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    signature = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    modalidad = models.CharField(
        max_length=1,
        choices=MODALIDAD_CHOICES,
        default='I',
        help_text="I: individual, G: grupal, S: superadmin"
    )

    plan = models.CharField(
        max_length=2,
        default='M',
        help_text="M: mensual, A: anual, D: demo, NT: no tiene"
    )

    # ✅ NUEVO: cupo máximo de auditores para modalidad grupal (mínimo 3)
    auditor_slots = models.PositiveIntegerField(
        default=3,
        help_text="Cantidad máxima de auditores permitidos para este jefe de auditoría (modalidad grupal)."
    )

    # ✅ Socio (una sola vez, evita duplicarlo)
    socio = models.BooleanField(
        default=False,
        help_text="Indica si el Jefe de Auditoría tiene privilegios de socio para crear usuarios."
    )

    administrador = models.ForeignKey(
        'self',
        related_name='auditores',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Administrador al que está asociado este usuario (para modalidad grupal)"
    )

    role = models.ForeignKey(
        'Roles',
        related_name="role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    revisor_fiscal = models.BooleanField(
        default=False,
        help_text="Indica si el usuario tiene acceso al módulo de Revisoría Fiscal."
    )

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.username}"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def is_admin(self):
        """True si es jefe de auditoría (audit_manager)."""
        return bool(self.role and self.role.name == "audit_manager")

    def get_auditores(self):
        """Retorna auditores asociados a este admin."""
        if not self.is_admin():
            return User.objects.none()
        return self.auditores.all()

    def deactivate_user(self, deactivation_date=None):
        if deactivation_date is None:
            deactivation_date = timezone.now()

        self.is_deleted = True
        self.deleted_at = deactivation_date
        self.save()

        if self.is_admin() and self.modalidad == 'G':
            for auditor in self.get_auditores():
                if not auditor.is_deleted:
                    auditor.is_deleted = True
                    auditor.deleted_at = deactivation_date
                    auditor.save()
        return True

    def reactivate_user(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

        auditores_reactivados = 0
        if self.is_admin() and self.modalidad == 'G':
            for auditor in self.get_auditores():
                if auditor.is_deleted:
                    auditor.is_deleted = False
                    auditor.deleted_at = None
                    auditor.save()
                    auditores_reactivados += 1
        return auditores_reactivados

    @property
    def can_create_users(self):
        return self.is_superuser or (self.is_admin() and self.socio)

class RegistroInvitacion(models.Model):
    """
    Invitaciones que envía un socio para que otra persona se autoregistre.
    El token se usa para construir el enlace de un solo uso.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    socio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="invitaciones_enviadas",
    )
    token = models.CharField(max_length=64, unique=True)
    usado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(default=timezone.now)
    usado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invitación a {self.email} (usado={self.usado})"