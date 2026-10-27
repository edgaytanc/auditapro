"""
Controles de acceso para el módulo Herramientas.

Centraliza la validación de:

- Auditoría seleccionada en sesión.
- Pertenencia al equipo.
- Asignación del usuario.
- Permisos de Papeles de Trabajo.
- Pertenencia del registro a la auditoría seleccionada.
"""

from typing import Optional, Type

from django.db.models import Model, QuerySet
from django.http import (
    Http404,
    HttpRequest,
)
from django.shortcuts import get_object_or_404

from audits.access import (
    get_audit_for_user_or_404,
)


TOOLS_PERMISSION_MODULE = (
    "workpapers"
)


def get_selected_audit_id(
    request: HttpRequest,
) -> int:
    """
    Obtiene de forma segura el ID de la auditoría
    seleccionada.

    Prioridad:

    1. request.selected_audit, agregado por
       selected_audit_required.
    2. request.session["selected_audit"].

    Devuelve 404 si la selección no existe o
    contiene un ID inválido.
    """

    selected_audit = getattr(
        request,
        "selected_audit",
        None,
    )

    if selected_audit is None:
        selected_audit = request.session.get(
            "selected_audit"
        )

    if not selected_audit:
        raise Http404(
            "No existe una auditoría seleccionada."
        )

    if isinstance(
        selected_audit,
        dict,
    ):
        audit_id = selected_audit.get(
            "id"
        )

    else:
        audit_id = getattr(
            selected_audit,
            "id",
            None,
        )

    try:
        normalized_audit_id = int(
            audit_id
        )

    except (
        TypeError,
        ValueError,
    ):
        raise Http404(
            "La auditoría seleccionada no es válida."
        )

    if normalized_audit_id <= 0:
        raise Http404(
            "La auditoría seleccionada no es válida."
        )

    return normalized_audit_id


def get_selected_audit_for_user_or_404(
    request: HttpRequest,
    action: str = "view",
):
    """
    Recupera la auditoría seleccionada y vuelve
    a comprobar el acceso del usuario.

    El control central valida:

    - Existencia de la auditoría.
    - Equipo propietario.
    - Asignación del integrante.
    - Permiso de Papeles de Trabajo.
    """

    audit_id = get_selected_audit_id(
        request
    )

    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action=action,
        module=TOOLS_PERMISSION_MODULE,
    )

    request.selected_audit = audit

    return audit


def get_tool_record_for_user_or_404(
    request: HttpRequest,
    model: Type[Model],
    record_id: int,
    action: str = "view",
    queryset: Optional[QuerySet] = None,
):
    """
    Recupera un registro de Herramientas después
    de comprobar que pertenece exactamente a la
    auditoría seleccionada.

    Todos los modelos operativos de Herramientas
    utilizados aquí deben tener un campo ForeignKey
    llamado `audit`.

    Args:
        request:
            Solicitud autenticada.

        model:
            Modelo que se quiere consultar.

        record_id:
            ID del registro solicitado.

        action:
            Acción exigida en la matriz:
            view, create, edit o delete.

        queryset:
            QuerySet opcional con select_related,
            prefetch_related u otras optimizaciones.

    Returns:
        Instancia del registro solicitado.

    Raises:
        Http404:
            Cuando el registro no existe, es de otra
            auditoría o el usuario no tiene acceso.
    """

    audit = get_selected_audit_for_user_or_404(
        request,
        action=action,
    )

    try:
        normalized_record_id = int(
            record_id
        )

    except (
        TypeError,
        ValueError,
    ):
        raise Http404(
            "El registro solicitado no es válido."
        )

    if normalized_record_id <= 0:
        raise Http404(
            "El registro solicitado no es válido."
        )

    if queryset is None:
        queryset = model.objects.all()

    # No se filtra por auditor=req.user porque el Jefe,
    # Supervisor u otros roles autorizados pueden consultar
    # registros creados por integrantes de su mismo equipo.
    #
    # El aislamiento se realiza por la auditoría seleccionada.
    return get_object_or_404(
        queryset,
        pk=normalized_record_id,
        audit_id=audit.id,
    )


def tool_record_belongs_to_selected_audit(
    request: HttpRequest,
    record,
) -> bool:
    """
    Comprueba si una instancia ya recuperada pertenece
    a la auditoría seleccionada.

    Se utiliza para validaciones adicionales en servicios
    o procesos internos.
    """

    try:
        selected_audit_id = (
            get_selected_audit_id(
                request
            )
        )

    except Http404:
        return False

    record_audit_id = getattr(
        record,
        "audit_id",
        None,
    )

    return (
        record_audit_id
        == selected_audit_id
    )