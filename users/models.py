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
        ('S', 'Superadmin'),  
    ]
    
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    signature = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    modalidad = models.CharField(
        max_length=1,
        choices=MODALIDAD_CHOICES,
        default='I',
        help_text="Indica si el usuario pertenece a modalidad individual (I), grupal (G) o es superadmin (S)"
    )
    
    plan = models.CharField(
        max_length=2,  
        default='M',
        help_text="Letra que identifica el plan específico (M: mensual, NT: no tiene plan, etc.)"
    )
    
        #  Campo que indica si el Jefe de Auditoría es socio
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
        Roles,
        related_name="role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    # Nuevo campo, indica si un jefe de auditoría es “Socio”
    socio = models.BooleanField(
        default=False,
        help_text="Define si el Jefe de Auditoría tiene privilegios de socio (puede crear usuarios)."
    )

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

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
        return self.role and self.role.name == "audit_manager"
    
    def get_auditores(self):
        """Obtiene todos los auditores asociados a este administrador."""
        if not self.is_admin():
            return User.objects.none()
        return self.auditores.all()

    def deactivate_user(self, deactivation_date=None):
        """
        Da de baja a un usuario y a sus auditores asociados si es un administrador en modalidad grupal.
        """
        from django.utils import timezone
        
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
        """Reactiva un usuario y sus auditores si aplica."""
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

    #  NUEVO MÉTODO: determina si puede crear usuarios
    @property
    def can_create_users(self):
        """
        Retorna True si el usuario puede crear otros usuarios.
        - Superadmin siempre puede.
        - Jefe de Auditoría solo si tiene socio=True.
        """
        return self.is_superuser or (self.role and self.role.name == 'audit_manager' and self.socio)
