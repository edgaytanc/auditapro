from django.db import IntegrityError, transaction
from django.db.models import F

from .models import CupoConsultasIA


class SinCupo(Exception):
    pass


def obtener_cupo(usuario):
    try:
        cupo, _ = CupoConsultasIA.objects.get_or_create(usuario=usuario)
    except IntegrityError:
        cupo = CupoConsultasIA.objects.get(usuario=usuario)
    return cupo


def reservar_consulta(usuario):
    """Descuento atómico: dos pestañas concurrentes no pueden gastar el mismo cupo."""
    cupo = obtener_cupo(usuario)
    actualizados = CupoConsultasIA.objects.filter(pk=cupo.pk, restantes__gt=0).update(
        restantes=F("restantes") - 1,
        realizadas=F("realizadas") + 1,
    )
    if not actualizados:
        raise SinCupo()
    return cupo.pk, cupo.version_cupo


def devolver_consulta(cupo_id, version):
    """Reintegra un fallo SOLO si el admin no recargó mientras estaba en proceso."""
    CupoConsultasIA.objects.filter(pk=cupo_id, version_cupo=version).update(
        restantes=F("restantes") + 1,
        realizadas=F("realizadas") - 1,
    )


@transaction.atomic
def recargar_cinco(usuario):
    """Nuevo cupo total de 5, NO acumulativo, por solicitud del administrador."""
    cupo = obtener_cupo(usuario)
    CupoConsultasIA.objects.filter(pk=cupo.pk).update(
        restantes=5,
        version_cupo=F("version_cupo") + 1,
    )
    cupo.refresh_from_db()
    return cupo
