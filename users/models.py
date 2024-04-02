from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    TIPOS_DE_USUARIO = (
        ('jefe_auditoria', 'Jefe de Auditoria'),
        ('supervisor', 'Supervisor'),
        ('auditor', 'Auditor'),
    )

    tipo_usuario = models.CharField(max_length=20, choices = TIPOS_DE_USUARIO, default='auditor')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    
