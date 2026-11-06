"""Almacenamiento privado de los archivos de Audita Análisis.

Los archivos del cliente viven fuera de ``static/`` y ``media/``: nunca se sirven por una ruta
pública, solo a través de vistas que comprueban el acceso a la auditoría.
"""
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage


class PrivateStorage(FileSystemStorage):
    """Lee la carpeta de ``ANALISIS_STORAGE_ROOT`` en cada uso (así se puede cambiar por entorno)."""

    @property
    def base_location(self):
        return str(settings.ANALISIS_STORAGE_ROOT)

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    @property
    def base_url(self):
        return None


def get_private_storage() -> PrivateStorage:
    return PrivateStorage()


def document_path(instance, filename: str) -> str:
    """Nombre interno aleatorio; el nombre original se guarda aparte en la base de datos."""
    ext = Path(filename).suffix.lower()
    return f"corrida_{instance.corrida_id}/docs/{uuid.uuid4().hex}{ext}"


def version_path(instance, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return f"corrida_{instance.corrida_id}/salidas/{uuid.uuid4().hex}{ext}"


def proyecto_path(instance, filename: str) -> str:
    """Archivos del flujo de hallazgos: por auditoría, con nombre interno aleatorio."""
    ext = Path(filename).suffix.lower()
    return f"auditoria_{instance.audit_id}/flujo/{uuid.uuid4().hex}{ext}"
