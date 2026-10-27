"""
Vistas para descarga de documentos de auditoría.

Contiene funciones para descargar documentos por:
- Carpeta y nombre de archivo.
- Patrón de referencia, por ejemplo A-1 o R-10.

Toda descarga valida:
- Que el usuario pertenezca al equipo correcto.
- Que esté asignado a la auditoría.
- Que tenga Papeles de Trabajo → Ver.
"""

import logging
import os
import urllib.parse

from audits.access import (
    get_audit_for_user_or_404,
    allowed_audit_type_codes,
)
from django.http import Http404
from auditoria.services.audit_mark_processor import (
    AuditMarkProcessor,
)

from .config import (
    FileResponse,
    HttpResponse,
    get_file_info_from_pattern,
    io,
    login_required,
    mark_safe,
    modify_document_excel,
    modify_document_excel_with_macros,
    modify_document_word,
)
from .utils import (
    crear_mensaje_error,
    get_template_path,
)


logger = logging.getLogger(__name__)


def _get_document_type(request, audit):
    """Respeta el tipo elegido y los enlaces heredados sin parámetro tipo."""
    authorized = allowed_audit_type_codes(request.user, audit)
    explicit_type = request.GET.get('tipo')
    audit_type = explicit_type or (audit.tipoAuditoria if audit.tipoAuditoria in authorized
                                    else (authorized[0] if authorized else None))
    if audit_type not in authorized:
        raise Http404('Este tipo de auditoría no está habilitado.')
    return audit_type


def _apply_revisoria_dynamic_content(
    workbook,
    audit,
    filename,
):
    """
    Actualiza archivos centralizadores de Revisoría Fiscal
    cuando corresponde.

    Si ocurre un error, permite continuar con la descarga.
    """

    is_revisoria_centralizer = (
        getattr(
            audit,
            "activa_revisoria",
            False,
        )
        and "CENTRALIZADORA"
        in filename.upper()
    )

    if not is_revisoria_centralizer:
        return workbook

    try:
        from auditoria.revisoria.activo import (
            update_dynamic_excel,
        )

        target_sheet = "Hoja1"

        if target_sheet in workbook.sheetnames:
            return update_dynamic_excel(
                workbook,
                target_sheet,
                audit.id,
            )

        logger.warning(
            (
                "'Hoja1' no encontrada en %s. "
                "Hojas disponibles: %s. "
                "Se omite update_dynamic_excel."
            ),
            filename,
            workbook.sheetnames,
        )

    except Exception as error:
        logger.warning(
            (
                "Error en update_dynamic_excel "
                "para Revisoría Fiscal: %s"
            ),
            error,
        )

    return workbook


def _process_word_document(
    template_path,
    audit,
    filename,
    folder,
    audit_type,
):
    """
    Genera un documento Word con los datos de la auditoría
    y aplica las marcas correspondientes.
    """

    buffer = io.BytesIO()

    document = modify_document_word(
        template_path,
        audit,
    )

    try:
        processor = AuditMarkProcessor(
            audit.id,
            filename,
        )

        document = (
            processor.process_word_document(
                document
            )
        )

    except Exception as error:
        logger.warning(
            (
                "No se pudieron agregar marcas "
                "de auditoría para %s: %s"
            ),
            filename,
            error,
        )

    # La descarga directa debe insertar la Ref. propia igual que el
    # generador con datos Auditor/Jefe. Reutilizar el inyector productivo,
    # que contempla los cuadros de texto de Word (incluidos mc:Fallback).
    try:
        from auditoria.services.referencias import (
            obtener_ref, inyectar_ref_propia_word,
        )
        referencia = obtener_ref(
            audit_type, folder, filename, audit_id=audit.id,
        )
        if referencia:
            document = inyectar_ref_propia_word(document, referencia)
    except Exception:
        logger.exception(
            "No se pudo insertar la referencia de %s (%s/%s)",
            filename, audit_type, audit.id,
        )

    document.save(
        buffer
    )

    buffer.seek(0)

    return (
        buffer,
        (
            "application/vnd.openxmlformats-officedocument."
            "wordprocessingml.document"
        ),
    )


def _process_excel_document(
    template_path,
    audit,
    filename,
    folder,
    audit_type,
):
    """
    Genera un documento Excel, aplica marcas de auditoría
    y actualiza la información de Revisoría Fiscal.
    """

    buffer = io.BytesIO()

    workbook = modify_document_excel(
        template_path,
        audit,
    )

    try:
        processor = AuditMarkProcessor(
            audit.id,
            filename,
        )

        workbook = (
            processor.process_excel_document(
                workbook
            )
        )

    except Exception as error:
        logger.warning(
            (
                "No se pudieron agregar marcas "
                "de auditoría para %s: %s"
            ),
            filename,
            error,
        )

    workbook = (
        _apply_revisoria_dynamic_content(
            workbook,
            audit,
            filename,
        )
    )

    # Inyectar Ref. después de los procesadores existentes y ANTES de
    # guardar, respetando cualquier referencia manual guardada por el auditor.
    try:
        from auditoria.services.referencias import (
            obtener_ref, inyectar_ref_propia,
        )
        referencia = obtener_ref(
            audit_type, folder, filename, audit_id=audit.id,
        )
        if referencia:
            workbook = inyectar_ref_propia(workbook, referencia)
    except Exception:
        logger.exception(
            "No se pudo insertar la referencia de %s (%s/%s)",
            filename, audit_type, audit.id,
        )

    workbook.save(
        buffer
    )

    buffer.seek(0)

    return (
        buffer,
        (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


def _process_excel_with_macros(
    template_path,
    audit,
    filename,
):
    """
    Procesa un archivo XLSM conservando sus macros.

    Los XLSM no reciben marcas de auditoría para evitar
    alterar o dañar el contenido VBA.
    """

    buffer = io.BytesIO()

    processed_file_path = (
        modify_document_excel_with_macros(
            template_path,
            audit,
        )
    )

    logger.info(
        (
            "Archivo XLSM %s: se omite el procesamiento "
            "de marcas de auditoría."
        ),
        filename,
    )

    with open(
        processed_file_path,
        "rb",
    ) as processed_file:
        buffer.write(
            processed_file.read()
        )

    buffer.seek(0)

    return (
        buffer,
        (
            "application/vnd.ms-excel."
            "sheet.macroEnabled.12"
        ),
    )


def _build_processed_response(
    template_path,
    audit,
    filename,
    folder,
    audit_type,
):
    """
    Procesa el archivo según su extensión y construye
    la respuesta de descarga.
    """

    lower_filename = filename.lower()

    if lower_filename.endswith(
        ".docx"
    ):
        buffer, content_type = (
            _process_word_document(
                template_path,
                audit,
                filename,
                folder,
                audit_type,
            )
        )

    elif lower_filename.endswith(
        ".xlsx"
    ):
        buffer, content_type = (
            _process_excel_document(
                template_path,
                audit,
                filename,
                folder,
                audit_type,
            )
        )

    elif lower_filename.endswith(
        ".xlsm"
    ):
        buffer, content_type = (
            _process_excel_with_macros(
                template_path,
                audit,
                filename,
            )
        )

    else:
        return FileResponse(
            open(
                template_path,
                "rb",
            ),
            as_attachment=True,
            filename=os.path.basename(
                template_path
            ),
        )

    response = FileResponse(
        buffer,
        as_attachment=True,
        filename=os.path.basename(
            template_path
        ),
    )

    response["Content-Type"] = (
        content_type
    )

    return response


@login_required
def download_document(
    request,
    audit_id,
    folder,
    filename,
):
    """
    Descarga un documento identificado por carpeta
    y nombre de archivo.

    La autorización se ejecuta antes de procesar
    o abrir cualquier plantilla.
    """

    folder = urllib.parse.unquote(
        folder
    )

    filename = urllib.parse.unquote(
        filename
    )

    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action="view",
        module="workpapers",
    )

    audit_type = _get_document_type(request, audit)
    is_internal = audit_type == "I"

    template_path = get_template_path(
        folder,
        filename,
        is_internal=is_internal,
        audit_type=audit_type,
    )

    if (
        not template_path
        or not os.path.exists(
            template_path
        )
    ):
        return HttpResponse(
            (
                "Plantilla no encontrada: "
                f"{folder}/{filename}"
            ),
            status=404,
        )

    try:
        return _build_processed_response(
            template_path,
            audit,
            filename,
            folder,
            audit_type,
        )

    except Exception as error:
        logger.exception(
            (
                "Error al descargar el documento "
                "%s de la auditoría %s."
            ),
            filename,
            audit.id,
        )

        return HttpResponse(
            (
                "Error al descargar documento: "
                f"{str(error)}"
            ),
            status=500,
        )


@login_required
def download_document_by_pattern(
    request,
    audit_id,
    pattern,
):
    """
    Descarga el archivo asociado a un patrón generado
    dentro de un documento.

    Ejemplos de patrones:
    - A-1
    - R-10
    - I-2

    La autorización se realiza antes del bloque general
    de procesamiento para conservar la respuesta 404
    de seguridad.
    """

    pattern = urllib.parse.unquote(
        pattern
    )

    # Debe quedar fuera del try general.
    # Así una auditoría ajena devuelve 404 y no 500.
    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action="view",
        module="workpapers",
    )

    audit_type = _get_document_type(request, audit)
    is_internal = audit_type == "I"

    file_info = get_file_info_from_pattern(
        pattern,
        is_internal=is_internal,
        audit_type=audit_type,
    )

    if not file_info:
        # Los catálogos de plantillas de octubre cambiaron sus nombres/rutas.
        # Intentar resolver la referencia sobre el árbol F/I/R ACTUAL sin
        # alterar los mapeos productivos ni apuntar a archivos inexistentes.
        from auditoria.services.referencias import construir_indice
        from django.conf import settings
        from pathlib import Path
        roots = {"F": "templates_base_financiera", "I": "templates_base_interna", "R": "templates_base_revisoria"}
        root = (Path(settings.BASE_DIR) / "static" / roots[audit_type]).resolve()
        for (candidate_folder, candidate_filename), ref in construir_indice(audit_type).items():
            if ref != pattern:
                continue
            candidate_path = (root / candidate_folder / candidate_filename).resolve()
            if root in candidate_path.parents and candidate_path.is_file():
                file_info = {"folder": candidate_folder, "filename": candidate_filename, "full_path": str(candidate_path)}
                break

    if not file_info:
        error_message = crear_mensaje_error(
            "Archivo no encontrado",
            (
                "No se pudo encontrar el archivo "
                "correspondiente al patrón: "
                f"<strong>{pattern}</strong><br>"
                "Verifique que el patrón sea correcto "
                "e intente nuevamente."
            ),
        )

        return HttpResponse(
            mark_safe(
                error_message
            ),
            status=404,
        )

    folder = file_info[
        "folder"
    ]

    filename = file_info[
        "filename"
    ]

    template_path = file_info[
        "full_path"
    ]

    if not os.path.exists(
        template_path
    ):
        error_message = crear_mensaje_error(
            "Plantilla no encontrada",
            (
                "No se encontró la plantilla: "
                f"{folder}/{filename}"
            ),
        )

        return HttpResponse(
            mark_safe(
                error_message
            ),
            status=404,
        )

    try:
        return _build_processed_response(
            template_path,
            audit,
            filename,
            folder,
            audit_type,
        )

    except Exception as error:
        logger.exception(
            (
                "Error procesando el patrón %s "
                "para la auditoría %s."
            ),
            pattern,
            audit.id,
        )

        error_message = crear_mensaje_error(
            "Error al procesar documento",
            (
                "Ocurrió un error al procesar "
                f"el documento {pattern}: "
                f"{str(error)}"
            ),
        )

        return HttpResponse(
            mark_safe(
                error_message
            ),
            status=500,
        )