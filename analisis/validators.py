"""Validación de archivos subidos: tipo real (no solo extensión), tamaño y bombas zip.

Se aplica antes de guardar nada en el expediente. Los errores son ``UploadRejected``
con un mensaje en español listo para mostrar al auditor.
"""
from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .engine.readers import KIND_BY_EXT, kind_for


class UploadRejected(Exception):
    """Archivo que no se acepta; ``args[0]`` es el motivo para el usuario."""


@dataclass
class UploadLimits:
    max_file_bytes: int
    max_total_bytes: int
    max_files: int
    max_unzipped_bytes: int
    max_zip_ratio: int

    @classmethod
    def from_settings(cls) -> "UploadLimits":
        return cls(
            max_file_bytes=settings.ANALISIS_MAX_FILE_MB * 1024 * 1024,
            max_total_bytes=settings.ANALISIS_MAX_TOTAL_MB * 1024 * 1024,
            max_files=settings.ANALISIS_MAX_FILES,
            max_unzipped_bytes=settings.ANALISIS_MAX_UNZIPPED_MB * 1024 * 1024,
            max_zip_ratio=settings.ANALISIS_MAX_ZIP_RATIO,
        )


_MAGIC = {
    "pdf": (b"%PDF-",),
    "imagen": (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*"),
}
_OOXML_MARKER = {
    "excel": "xl/workbook.xml",
    "word": "word/document.xml",
}


def allowed_extensions() -> list[str]:
    return sorted(KIND_BY_EXT)


def _check_zip(path: Path, kind: str, limits: UploadLimits) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            names = {i.filename for i in infos}
            if "[Content_Types].xml" not in names or _OOXML_MARKER[kind] not in names:
                raise UploadRejected("El contenido del archivo no corresponde a su extensión.")
            unzipped = sum(i.file_size for i in infos)
            if unzipped > limits.max_unzipped_bytes:
                raise UploadRejected("El archivo descomprimido es demasiado grande.")
            compressed = max(sum(i.compress_size for i in infos), 1)
            if unzipped / compressed > limits.max_zip_ratio and unzipped > 50 * 1024 * 1024:
                raise UploadRejected("El archivo tiene una compresión sospechosa y no se acepta.")
            if any(i.filename.startswith(("/", "..")) or ".." in Path(i.filename).parts for i in infos):
                raise UploadRejected("El archivo contiene rutas no permitidas.")
    except zipfile.BadZipFile:
        raise UploadRejected("El archivo está dañado o no es un documento de Office válido.") from None


def _check_csv(path: Path) -> None:
    with path.open("rb") as fh:
        head = fh.read(8192)
    if b"\x00" in head:
        raise UploadRejected("El CSV contiene datos binarios.")


def validate_saved_file(path: str | Path, original_name: str, limits: UploadLimits | None = None) -> str:
    """Comprueba un archivo ya escrito en disco. Devuelve el formato (``kind``)."""
    limits = limits or UploadLimits.from_settings()
    path = Path(path)
    ext = Path(original_name).suffix.lower()
    kind = kind_for(original_name)
    if kind is None:
        raise UploadRejected(
            f"Formato no permitido: {original_name}. Use Excel (.xlsx), CSV, Word (.docx), PDF o imagen."
        )
    size = path.stat().st_size
    if size == 0:
        raise UploadRejected(f"El archivo {original_name} está vacío.")
    if size > limits.max_file_bytes:
        raise UploadRejected(
            f"{original_name} supera el máximo de {limits.max_file_bytes // (1024 * 1024)} MB por archivo."
        )
    if kind in _OOXML_MARKER:
        _check_zip(path, kind, limits)
    elif kind in _MAGIC:
        with path.open("rb") as fh:
            head = fh.read(16)
        if not any(head.startswith(m) for m in _MAGIC[kind]):
            raise UploadRejected(f"{original_name}: el contenido no corresponde a su extensión ({ext}).")
    elif kind == "csv":
        _check_csv(path)
    return kind


def sha256_of(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
