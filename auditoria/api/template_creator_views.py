"""
API Views para el Creador de Plantillas Excel Dinámico.

Endpoints:
1. POST /api/validate-workbook-name
2. POST /api/validate-template-config
3. GET  /api/symbols/library
4. POST /api/generate-template
5. GET  /api/audit/{id}/marks

Seguridad:
- Requiere autenticación.
- Valida el acceso a la auditoría.
- Valida pertenencia al mismo equipo.
- Exige estar asignado, salvo el Jefe.
- Aplica permisos de Papeles de Trabajo.
"""

import json
import logging
import os

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import (
    Http404,
    HttpResponse,
    JsonResponse,
)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from audits.access import (
    get_audit_for_user_or_404,
)

from auditoria.models import (
    AuditMark,
    SymbolLibrary,
    TemplateColumn,
    TemplateConfiguration,
    TemplateSymbol,
)
from auditoria.services.dynamic_template_generator import (
    DynamicTemplateGenerator,
)
from auditoria.services.symbol_library_service import (
    SymbolLibraryService,
)
from auditoria.services.template_config_validator import (
    TemplateConfigValidator,
)


logger = logging.getLogger(__name__)


EXCEL_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)


def _json_error(
    message,
    status=400,
):
    """
    Construye una respuesta JSON uniforme de error.
    """

    return JsonResponse(
        {
            "error": message,
        },
        status=status,
    )


def _parse_json_body(
    request,
):
    """
    Convierte el cuerpo JSON en un diccionario.

    Lanza json.JSONDecodeError cuando el contenido
    no es un JSON válido.
    """

    data = json.loads(
        request.body or b"{}"
    )

    if not isinstance(
        data,
        dict,
    ):
        raise json.JSONDecodeError(
            "El cuerpo debe ser un objeto JSON.",
            str(data),
            0,
        )

    return data


def _parse_boolean(
    value,
    default=False,
):
    """
    Convierte valores de formulario o JSON a booleano.
    """

    if value is None:
        return default

    if isinstance(
        value,
        bool,
    ):
        return value

    return str(
        value
    ).strip().lower() in {
        "true",
        "1",
        "yes",
        "on",
        "si",
        "sí",
    }


def _get_authorized_audit(
    user,
    audit_id,
    action,
):
    """
    Obtiene una auditoría aplicando el control central.

    Returns:
        tuple:
            audit, None cuando el acceso es válido.
            None, JsonResponse cuando debe bloquearse.
    """

    try:
        normalized_audit_id = int(
            audit_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            None,
            _json_error(
                "El audit_id no es válido.",
                status=400,
            ),
        )

    try:
        audit = get_audit_for_user_or_404(
            user,
            normalized_audit_id,
            action=action,
            module="workpapers",
        )

    except Http404:
        return (
            None,
            _json_error(
                (
                    "La auditoría no existe "
                    "o no tienes acceso."
                ),
                status=404,
            ),
        )

    return (
        audit,
        None,
    )


# ═════════════════════════════════════════════════════════════
# ENDPOINT 1: Validar nombre del Workbook
# ═════════════════════════════════════════════════════════════

@csrf_exempt
@login_required
@require_http_methods(
    [
        "POST",
    ]
)
def validate_workbook_name(
    request,
):
    """
    Valida en tiempo real el nombre de un Workbook.

    Requiere:
    - Papeles de Trabajo → Crear.
    - Auditoría del mismo equipo.
    - Usuario asignado, salvo el Jefe.
    """

    try:
        data = _parse_json_body(
            request
        )

    except json.JSONDecodeError:
        return _json_error(
            "JSON inválido.",
            status=400,
        )

    audit_id = data.get(
        "audit_id"
    )

    workbook_name = str(
        data.get(
            "workbook_name",
            "",
        )
    ).strip()

    if not audit_id:
        return _json_error(
            "audit_id es requerido.",
            status=400,
        )

    audit, access_error = (
        _get_authorized_audit(
            request.user,
            audit_id,
            action="create",
        )
    )

    if access_error:
        return access_error

    if not workbook_name:
        return JsonResponse(
            {
                "is_valid": False,
                "message": (
                    "El nombre del libro de trabajo "
                    "no puede estar vacío."
                ),
                "suggestions": [],
                "is_excluded": False,
            },
            status=200,
        )

    try:
        validator = TemplateConfigValidator(
            audit.id
        )

        result = (
            validator
            .validate_workbook_name_only(
                workbook_name
            )
        )

        logger.debug(
            (
                "Validación del Workbook %s "
                "para auditoría %s: valid=%s"
            ),
            workbook_name,
            audit.id,
            result.get(
                "is_valid"
            ),
        )

        return JsonResponse(
            result,
            status=200,
        )

    except Exception as error:
        logger.exception(
            (
                "Error validando el nombre del "
                "Workbook para auditoría %s."
            ),
            audit.id,
        )

        return _json_error(
            (
                "Error del servidor: "
                f"{str(error)}"
            ),
            status=500,
        )


# ═════════════════════════════════════════════════════════════
# ENDPOINT 2: Validar configuración completa
# ═════════════════════════════════════════════════════════════

@csrf_exempt
@login_required
@require_http_methods(
    [
        "POST",
    ]
)
def validate_template_config(
    request,
):
    """
    Valida una configuración completa antes de generar
    una plantilla.

    Requiere Papeles de Trabajo → Crear.
    """

    try:
        data = _parse_json_body(
            request
        )

    except json.JSONDecodeError:
        return _json_error(
            "JSON inválido.",
            status=400,
        )

    audit_id = data.get(
        "audit_id"
    )

    if not audit_id:
        return _json_error(
            "audit_id es requerido.",
            status=400,
        )

    audit, access_error = (
        _get_authorized_audit(
            request.user,
            audit_id,
            action="create",
        )
    )

    if access_error:
        return access_error

    try:
        validator = TemplateConfigValidator(
            audit.id
        )

        result = (
            validator
            .validate_full_configuration(
                data
            )
        )

        summary = result.get(
            "summary",
            {},
        )

        logger.info(
            (
                "Validación de plantilla para "
                "auditoría %s: valid=%s, errors=%s"
            ),
            audit.id,
            result.get(
                "is_valid"
            ),
            summary.get(
                "total_errors",
                0,
            ),
        )

        return JsonResponse(
            result,
            status=200,
        )

    except Exception as error:
        logger.exception(
            (
                "Error validando la configuración "
                "para auditoría %s."
            ),
            audit.id,
        )

        return _json_error(
            (
                "Error del servidor: "
                f"{str(error)}"
            ),
            status=500,
        )


# ═════════════════════════════════════════════════════════════
# ENDPOINT 3: Obtener biblioteca de símbolos
# ═════════════════════════════════════════════════════════════

@login_required
@require_http_methods(
    [
        "GET",
    ]
)
def get_symbols_library(
    request,
):
    """
    Obtiene la biblioteca de símbolos disponible.

    Requiere Papeles de Trabajo → Ver.
    """

    audit_id = request.GET.get(
        "audit_id"
    )

    include_custom = _parse_boolean(
        request.GET.get(
            "include_custom"
        ),
        default=True,
    )

    if not audit_id:
        return _json_error(
            "audit_id es requerido.",
            status=400,
        )

    audit, access_error = (
        _get_authorized_audit(
            request.user,
            audit_id,
            action="view",
        )
    )

    if access_error:
        return access_error

    try:
        symbols = (
            SymbolLibraryService
            .get_symbols_for_audit(
                audit.id,
                include_custom=(
                    include_custom
                ),
            )
        )

        symbols_data = [
            {
                "id": symbol.id,
                "symbol": symbol.symbol,
                "description": (
                    symbol.description
                ),
                "category": (
                    symbol.category
                ),
                "is_system": (
                    symbol.is_system
                ),
                "display_order": (
                    symbol.display_order
                ),
            }
            for symbol in symbols
        ]

        category_counts = (
            SymbolLibraryService
            .get_category_counts()
        )

        categories = {}

        for (
            category_value,
            category_label,
        ) in SymbolLibrary.CATEGORY_CHOICES:
            if (
                category_value
                in category_counts
            ):
                categories[
                    category_value
                ] = {
                    "label": (
                        category_label
                    ),
                    "count": (
                        category_counts[
                            category_value
                        ]
                    ),
                }

        response_data = {
            "symbols": symbols_data,
            "categories": categories,
            "total_count": len(
                symbols_data
            ),
        }

        logger.debug(
            (
                "Símbolos obtenidos para "
                "auditoría %s: %s"
            ),
            audit.id,
            len(
                symbols_data
            ),
        )

        return JsonResponse(
            response_data,
            status=200,
        )

    except Exception as error:
        logger.exception(
            (
                "Error obteniendo símbolos para "
                "auditoría %s."
            ),
            audit.id,
        )

        return _json_error(
            (
                "Error del servidor: "
                f"{str(error)}"
            ),
            status=500,
        )


# ═════════════════════════════════════════════════════════════
# ENDPOINT 4: Generar plantilla Excel
# ═════════════════════════════════════════════════════════════

@csrf_exempt
@login_required
@require_http_methods(
    [
        "POST",
    ]
)
def generate_template(
    request,
):
    """
    Genera una plantilla Excel y opcionalmente guarda
    su configuración en la base de datos.

    Requiere Papeles de Trabajo → Crear.
    """

    try:
        data = _parse_json_body(
            request
        )

    except json.JSONDecodeError:
        return _json_error(
            "JSON inválido.",
            status=400,
        )

    audit_id = data.get(
        "audit_id"
    )

    if not audit_id:
        return _json_error(
            "audit_id es requerido.",
            status=400,
        )

    audit, access_error = (
        _get_authorized_audit(
            request.user,
            audit_id,
            action="create",
        )
    )

    if access_error:
        return access_error

    save_config = _parse_boolean(
        data.get(
            "save_config"
        ),
        default=True,
    )

    try:
        validator = TemplateConfigValidator(
            audit.id
        )

        validation_result = (
            validator
            .validate_full_configuration(
                data
            )
        )

        if not validation_result.get(
            "is_valid",
            False,
        ):
            return JsonResponse(
                {
                    "error": (
                        "Configuración inválida."
                    ),
                    "validation_errors": (
                        validation_result.get(
                            "errors",
                            [],
                        )
                    ),
                },
                status=400,
            )

        data["audit_info"] = {
            "title": audit.title,
            "created_by": (
                request.user.get_full_name()
                or request.user.username
            ),
        }

        logger.info(
            (
                "Generando plantilla para "
                "auditoría %s, Workbook %s."
            ),
            audit.id,
            data.get(
                "workbook_name"
            ),
        )

        generator = DynamicTemplateGenerator(
            data
        )

        excel_file = generator.generate()

        if save_config:
            with transaction.atomic():
                template_config = (
                    TemplateConfiguration
                    .objects.create(
                        audit=audit,
                        workbook_name=data[
                            "workbook_name"
                        ],
                        created_by=(
                            request.user
                        ),
                        configuration_json=(
                            data
                        ),
                        download_count=1,
                        last_downloaded_at=(
                            timezone.now()
                        ),
                    )
                )

                for column_data in data.get(
                    "columns",
                    [],
                ):
                    TemplateColumn.objects.create(
                        template_config=(
                            template_config
                        ),
                        column_name=(
                            column_data[
                                "name"
                            ]
                        ),
                        column_order=(
                            column_data.get(
                                "order",
                                0,
                            )
                        ),
                        column_width=(
                            column_data.get(
                                "width",
                                15,
                            )
                        ),
                        data_type=(
                            column_data.get(
                                "data_type",
                                "text",
                            )
                        ),
                        is_required=(
                            column_data.get(
                                "is_required",
                                False,
                            )
                        ),
                    )

                for (
                    symbol_index,
                    symbol_data,
                ) in enumerate(
                    data.get(
                        "symbols",
                        [],
                    )
                ):
                    symbol_value = (
                        symbol_data.get(
                            "symbol"
                        )
                    )

                    if not symbol_value:
                        continue

                    symbol = (
                        SymbolLibrary.objects
                        .filter(
                            symbol=(
                                symbol_value
                            ),
                            is_active=True,
                        )
                        .first()
                    )

                    if symbol is None:
                        logger.warning(
                            (
                                "Símbolo no encontrado: "
                                "%s"
                            ),
                            symbol_value,
                        )

                        continue

                    TemplateSymbol.objects.create(
                        template_config=(
                            template_config
                        ),
                        symbol=symbol,
                        display_order=(
                            symbol_index
                        ),
                    )

                logger.info(
                    (
                        "Configuración guardada: "
                        "template_config_id=%s"
                    ),
                    template_config.id,
                )

        generated_filename = (
            generator.get_filename()
        )

        safe_filename = os.path.basename(
            generated_filename
        ).replace(
            '"',
            "",
        )

        response = HttpResponse(
            excel_file.getvalue(),
            content_type=(
                EXCEL_CONTENT_TYPE
            ),
        )

        response[
            "Content-Disposition"
        ] = (
            f'attachment; filename="{safe_filename}"'
        )

        logger.info(
            (
                "Plantilla generada correctamente: "
                "%s"
            ),
            safe_filename,
        )

        return response

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        logger.warning(
            (
                "Configuración inválida para "
                "auditoría %s: %s"
            ),
            audit.id,
            error,
        )

        return _json_error(
            (
                "La configuración contiene "
                "datos inválidos: "
                f"{str(error)}"
            ),
            status=400,
        )

    except Exception as error:
        logger.exception(
            (
                "Error generando plantilla para "
                "auditoría %s."
            ),
            audit.id,
        )

        return _json_error(
            (
                "Error del servidor: "
                f"{str(error)}"
            ),
            status=500,
        )


# ═════════════════════════════════════════════════════════════
# ENDPOINT 5: Obtener marcas de auditoría
# ═════════════════════════════════════════════════════════════

@login_required
@require_http_methods(
    [
        "GET",
    ]
)
def get_audit_marks(
    request,
    audit_id,
):
    """
    Obtiene las marcas existentes de una auditoría.

    Requiere Papeles de Trabajo → Ver.
    """

    audit, access_error = (
        _get_authorized_audit(
            request.user,
            audit_id,
            action="view",
        )
    )

    if access_error:
        return access_error

    include_inactive = _parse_boolean(
        request.GET.get(
            "include_inactive"
        ),
        default=False,
    )

    try:
        marks_query = AuditMark.objects.filter(
            audit=audit
        )

        if not include_inactive:
            marks_query = marks_query.filter(
                is_active=True
            )

        marks = marks_query.order_by(
            "work_paper_number",
            "created_at",
        )

        marks_data = [
            {
                "id": mark.id,
                "symbol": mark.symbol,
                "description": (
                    mark.description
                ),
                "work_paper_number": (
                    mark.work_paper_number
                    or ""
                ),
                "is_active": (
                    mark.is_active
                ),
            }
            for mark in marks
        ]

        response_data = {
            "marks": marks_data,
            "total_count": len(
                marks_data
            ),
        }

        logger.debug(
            (
                "Marcas obtenidas para "
                "auditoría %s: %s"
            ),
            audit.id,
            len(
                marks_data
            ),
        )

        return JsonResponse(
            response_data,
            status=200,
        )

    except Exception as error:
        logger.exception(
            (
                "Error obteniendo marcas para "
                "auditoría %s."
            ),
            audit.id,
        )

        return _json_error(
            (
                "Error del servidor: "
                f"{str(error)}"
            ),
            status=500,
        )