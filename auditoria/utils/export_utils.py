"""
Utilidades para exportar estados financieros.

La exportación conserva el comportamiento existente,
pero valida previamente el acceso del usuario a la
auditoría y al módulo de Papeles de Trabajo.
"""

import io
import os

import openpyxl

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (
    FileResponse,
    HttpResponse,
)

from audits.access import (
    get_audit_for_user_or_404,
)


@login_required
def export_cuentas_contables(
    request,
    audit_id,
    tipo,
):
    """
    Exporta la plantilla de estados financieros.

    Reglas de acceso:
    - La auditoría debe pertenecer al mismo equipo.
    - El usuario debe estar asignado, salvo que sea
      el Jefe de Auditoría.
    - Debe tener Papeles de Trabajo → Ver.

    Args:
        request:
            Solicitud HTTP autenticada.

        audit_id:
            Identificador de la auditoría.

        tipo:
            Tipo de exportación. Se conserva por
            compatibilidad con las URLs existentes.

    Returns:
        FileResponse:
            Archivo Excel descargable.

        HttpResponse:
            Error 404 cuando la plantilla no existe.
    """

    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action="view",
        module="workpapers",
    )

    # Se conserva el parámetro por compatibilidad,
    # aunque actualmente se utiliza una sola plantilla.
    _tipo_exportacion = tipo

    filename_template = (
        "ESTADOS-FINANCIEROS.xlsx"
    )

    template_path = os.path.join(
        settings.BASE_DIR,
        "static",
        "template-est-fin",
        filename_template,
    )

    if not os.path.exists(
        template_path
    ):
        return HttpResponse(
            (
                "No se encontró la plantilla "
                f"'{filename_template}'."
            ),
            status=404,
        )

    try:
        workbook = openpyxl.load_workbook(
            template_path
        )

        buffer = io.BytesIO()

        workbook.save(
            buffer
        )

        buffer.seek(0)

    except Exception as error:
        return HttpResponse(
            (
                "No fue posible preparar el archivo "
                "de estados financieros: "
                f"{str(error)}"
            ),
            status=500,
        )

    download_name = (
        f"ESTADOS-FINANCIEROS-{audit.id}.xlsx"
    )

    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=download_name,
    )

    response["Content-Type"] = (
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )

    return response