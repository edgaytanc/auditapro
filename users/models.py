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
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    signature = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

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
