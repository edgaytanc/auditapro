"""
Vistas para el sistema de marcas de auditoría.

Contiene:
- Carga del archivo Excel de marcas.
- Descarga de la plantilla modelo.

Reglas:
- Cargar marcas exige Papeles de Trabajo → Editar.
- Descargar la plantilla exige Papeles de Trabajo → Ver.
- La auditoría debe pertenecer al mismo equipo.
- El integrante debe estar asignado a la auditoría.
"""

import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import (
    login_required,
)
from django.http import (
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from audits.access import (
    get_audit_for_user_or_404,
)
from users.permissions import (
    module_permission_required,
)

from auditoria.services.audit_mark_import_service import (
    AuditMarkImportService,
)


logger = logging.getLogger(
    __name__
)


@login_required
@require_POST
def upload_audit_marks(
    request,
    audit_id,
):
    """
    Carga un archivo Excel con marcas de auditoría.

    Se requiere:
    - Papeles de Trabajo → Editar.
    - Auditoría del mismo equipo.
    - Usuario asignado, salvo el Jefe.
    """

    try:
        audit = get_audit_for_user_or_404(
            request.user,
            audit_id,
            action="edit",
            module="workpapers",
        )

    except Http404:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "La auditoría no existe "
                    "o no tienes acceso."
                ),
            },
            status=404,
        )

    excel_file = request.FILES.get(
        "excel_file"
    )

    if not excel_file:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "No se cargó ningún archivo."
                ),
            },
            status=400,
        )

    filename = (
        excel_file.name
        or ""
    ).lower()

    valid_extensions = {
        ".xlsx",
        ".xlsm",
    }

    file_extension = os.path.splitext(
        filename
    )[1]

    if file_extension not in valid_extensions:
        return JsonResponse(
            {
                "success": False,
                "error": (
                    "El archivo debe estar en formato "
                    "Excel .xlsx o .xlsm."
                ),
            },
            status=400,
        )

    replace_existing = (
        request.POST.get(
            "replace_existing"
        )
        == "on"
    )

    try:
        service = AuditMarkImportService(
            audit.id,
            excel_file,
        )

        result = service.import_marks(
            replace_existing=(
                replace_existing
            )
        )

        if not isinstance(
            result,
            dict,
        ):
            result = {
                "success": True,
                "message": str(
                    result
                ),
            }

        result.setdefault(
            "success",
            True,
        )

        return JsonResponse(
            result,
            status=200,
        )

    except ValueError as error:
        return JsonResponse(
            {
                "success": False,
                "error": str(
                    error
                ),
            },
            status=400,
        )

    except Exception as error:
        logger.exception(
            (
                "Error cargando marcas para "
                "la auditoría %s."
            ),
            audit.id,
        )

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "No fue posible importar "
                    "las marcas de auditoría: "
                    f"{str(error)}"
                ),
            },
            status=500,
        )


@login_required
@module_permission_required(
    "workpapers",
    "view",
)
@require_GET
def download_audit_mark_template(
    request,
):
    """
    Descarga la plantilla modelo de marcas.

    Al ser una plantilla general, no requiere un
    audit_id específico, pero sí permiso para
    consultar Papeles de Trabajo.
    """

    filename = (
        "MODELO DE MARCAS_DE_AUDITORIA_"
        "VINCULADO.xlsx"
    )

    modelo_path = os.path.join(
        settings.BASE_DIR,
        filename,
    )

    if not os.path.exists(
        modelo_path
    ):
        raise Http404(
            "Plantilla de marcas no encontrada."
        )

    try:
        with open(
            modelo_path,
            "rb",
        ) as excel_file:
            file_content = (
                excel_file.read()
            )

    except OSError:
        logger.exception(
            (
                "No fue posible leer la plantilla "
                "de marcas de auditoría."
            )
        )

        raise Http404(
            "Error al descargar la plantilla."
        )

    response = HttpResponse(
        file_content,
        content_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="'
        'MODELO_MARCAS_AUDITORIA.xlsx"'
    )

    response[
        "Content-Length"
    ] = len(
        file_content
    )

    return response