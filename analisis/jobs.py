"""Cola acotada de corridas para que el análisis no sobrecargue el servidor.

- Pocos trabajadores (``ANALISIS_MAX_WORKERS``) procesan las corridas de una en una.
- Hay un tope de corridas activas en total y por usuario: lo que lo excede se rechaza con un
  mensaje claro (contrapresión) en lugar de acumularse.
- Una corrida sin «latido» por demasiado tiempo (reinicio del servidor, proceso colgado) se
  marca con error para que no quede «ejecutando» para siempre.

Está pensado para un solo proceso web. Si en producción se ejecuta con varios procesos, el
tope global se sigue respetando (se cuenta en la base de datos) y las corridas pueden
reanudarse con ``python manage.py analisis_recuperar``.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, connection
from django.utils import timezone

from .models import BitacoraAnalisis, CorridaAnalisis

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    global _executor
    with _lock:
        if _executor is None:
            _executor = ThreadPoolExecutor(max_workers=settings.ANALISIS_MAX_WORKERS, thread_name_prefix="analisis")
        return _executor


def capacity_error(user) -> str | None:
    """Mensaje si no hay cupo para otra corrida; ``None`` si se puede encolar."""
    mark_stale()
    active = CorridaAnalisis.objects.filter(estado__in=CorridaAnalisis.ACTIVAS)
    if active.count() >= settings.ANALISIS_MAX_QUEUE:
        return "El sistema está procesando muchos análisis en este momento. Intente de nuevo en unos minutos."
    if active.filter(creado_por=user).count() >= settings.ANALISIS_MAX_ACTIVE_PER_USER:
        return (
            f"Ya tiene {settings.ANALISIS_MAX_ACTIVE_PER_USER} análisis en proceso. "
            "Espere a que termine alguno para iniciar otro."
        )
    return None


def mark_stale() -> int:
    limit = timezone.now() - timedelta(minutes=settings.ANALISIS_STALE_MINUTES)
    stale = list(CorridaAnalisis.objects.filter(estado__in=CorridaAnalisis.ACTIVAS, latido__lt=limit))
    for run in stale:
        run.estado = CorridaAnalisis.Estado.ERROR
        run.error_mensaje = "El análisis se interrumpió (reinicio del servidor o tiempo agotado). Vuelva a ejecutarlo."
        run.terminado_en = timezone.now()
        run.save(update_fields=["estado", "error_mensaje", "terminado_en"])
        BitacoraAnalisis.registrar(run, None, "interrumpida", {})
    return len(stale)


def _run(run_id: int) -> None:
    from .pipeline import execute_run

    close_old_connections()
    try:
        execute_run(run_id)
    except Exception:  # noqa: BLE001 - execute_run ya registra el error; esto es la última red de seguridad
        logger.exception("Audita Análisis: fallo no controlado en la corrida %s", run_id)
    finally:
        connection.close()


def submit(run_id: int) -> None:
    if settings.ANALISIS_RUN_INLINE:
        from .pipeline import execute_run

        execute_run(run_id)
        return
    _get_executor().submit(_run, run_id)
