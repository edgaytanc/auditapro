"""
API Views para el Creador de Plantillas Excel Dinámico

⚠️ ENDPOINTS:
1. POST /api/validate-workbook-name - Validación en tiempo real de nombre
2. POST /api/validate-template-config - Validación completa de configuración
3. GET /api/symbols/library - Obtener biblioteca de símbolos
4. POST /api/generate-template - Generar y descargar plantilla Excel
5. GET /api/audit/{id}/marks - Obtener marcas existentes de auditoría

SEGURIDAD:
- Requiere autenticación
- Valida permisos de auditoría
- No modifica archivos existentes
- Solo crea nuevos archivos en memoria
"""

from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.utils import timezone

from auditoria.services.symbol_library_service import SymbolLibraryService
from auditoria.services.dynamic_template_generator import DynamicTemplateGenerator
from auditoria.services.template_config_validator import TemplateConfigValidator
from auditoria.models import TemplateConfiguration, TemplateColumn, TemplateSymbol, AuditMark, SymbolLibrary
from audits.models import Audit

import json
import logging

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: Validar Nombre de Workbook (Tiempo Real)
# ══════════════════════════════════════════════════════════════════════════════
@require_http_methods(["POST"])
@login_required
@csrf_exempt
def validate_workbook_name(request):
    """
    POST /api/validate-workbook-name

    Valida un nombre de workbook en tiempo real contra archivos existentes.

    Request Body:
    {
        "audit_id": int,
        "workbook_name": str
    }

    Response:
    {
        "is_valid": bool,
        "message": str,
        "suggestions": List[str],
        "is_excluded": bool,
        "matched_files": List[str] (opcional)
    }
    """
    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')
        workbook_name = data.get('workbook_name', '').strip()

        # Validar parámetros
        if not audit_id:
            return JsonResponse({
                'error': 'audit_id es requerido'
            }, status=400)

        if not workbook_name:
            return JsonResponse({
                'is_valid': False,
                'message': 'El nombre del libro de trabajo no puede estar vacío',
                'suggestions': [],
                'is_excluded': False
            })

        # Verificar acceso a la auditoría
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse({
                'error': 'Auditoría no encontrada'
            }, status=404)

        # Validar nombre usando TemplateConfigValidator
        validator = TemplateConfigValidator(audit_id)
        result = validator.validate_workbook_name_only(workbook_name)

        logger.debug(
            f"Validación de workbook name: {workbook_name} - "
            f"valid={result['is_valid']}"
        )

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error en validate_workbook_name: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}'
        }, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: Validar Configuración Completa
# ══════════════════════════════════════════════════════════════════════════════
@require_http_methods(["POST"])
@login_required
@csrf_exempt
def validate_template_config(request):
    """
    POST /api/validate-template-config

    Valida una configuración completa de plantilla antes de generar.

    Request Body:
    {
        "audit_id": int,
        "workbook_name": str,
        "columns": [{name, width, data_type, is_required}],
        "symbols": [{symbol, description, category}],
        "options": {include_headers, include_instructions, ...}
    }

    Response:
    {
        "is_valid": bool,
        "errors": [{field, message, severity}],
        "warnings": [{field, message, severity}],
        "summary": {total_errors, total_warnings, ...}
    }
    """
    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')

        # Validar parámetros
        if not audit_id:
            return JsonResponse({
                'error': 'audit_id es requerido'
            }, status=400)

        # Verificar acceso a la auditoría
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse({
                'error': 'Auditoría no encontrada'
            }, status=404)

        # Validar configuración completa
        validator = TemplateConfigValidator(audit_id)
        result = validator.validate_full_configuration(data)

        logger.info(
            f"Validación completa para audit_id={audit_id}: "
            f"valid={result['is_valid']}, "
            f"errors={result['summary']['total_errors']}"
        )

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error en validate_template_config: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}'
        }, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: Obtener Biblioteca de Símbolos
# ══════════════════════════════════════════════════════════════════════════════
@require_http_methods(["GET"])
@login_required
def get_symbols_library(request):
    """
    GET /api/symbols/library?audit_id={audit_id}&include_custom={bool}

    Obtiene la biblioteca de símbolos disponibles.

    Query Parameters:
    - audit_id: int (requerido)
    - include_custom: bool (opcional, default=true)

    Response:
    {
        "symbols": [{
            "id": int,
            "symbol": str,
            "description": str,
            "category": str,
            "is_system": bool
        }],
        "categories": {
            "verification": {label, count},
            "calculation": {label, count},
            ...
        },
        "total_count": int
    }
    """
    try:
        audit_id = request.GET.get('audit_id')
        include_custom = request.GET.get('include_custom', 'true').lower() == 'true'

        # Validar parámetros
        if not audit_id:
            return JsonResponse({
                'error': 'audit_id es requerido'
            }, status=400)

        # Verificar acceso a la auditoría
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse({
                'error': 'Auditoría no encontrada'
            }, status=404)

        # Obtener símbolos
        symbols = SymbolLibraryService.get_symbols_for_audit(
            audit_id,
            include_custom=include_custom
        )

        # Serializar símbolos
        symbols_data = []
        for symbol in symbols:
            symbols_data.append({
                'id': symbol.id,
                'symbol': symbol.symbol,
                'description': symbol.description,
                'category': symbol.category,
                'is_system': symbol.is_system,
                'display_order': symbol.display_order
            })

        # Obtener conteos por categoría
        category_counts = SymbolLibraryService.get_category_counts()

        # Obtener etiquetas de categorías
        categories = {}
        for cat_value, cat_label in SymbolLibrary.CATEGORY_CHOICES:
            if cat_value in category_counts:
                categories[cat_value] = {
                    'label': cat_label,
                    'count': category_counts[cat_value]
                }

        response_data = {
            'symbols': symbols_data,
            'categories': categories,
            'total_count': len(symbols_data)
        }

        logger.debug(f"Símbolos obtenidos para audit_id={audit_id}: {len(symbols_data)}")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error en get_symbols_library: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}'
        }, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: Generar y Descargar Plantilla Excel
# ══════════════════════════════════════════════════════════════════════════════
@require_http_methods(["POST"])
@login_required
@csrf_exempt
@transaction.atomic
def generate_template(request):
    """
    POST /api/generate-template

    Genera una plantilla Excel y la devuelve para descarga.
    También guarda la configuración en la base de datos.

    Request Body:
    {
        "audit_id": int,
        "workbook_name": str,
        "columns": [{name, width, data_type, is_required}],
        "symbols": [{symbol, description, category}],
        "options": {include_headers, include_instructions, ...},
        "save_config": bool (opcional, default=true)
    }

    Response:
    Binary Excel file (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
    """
    try:
        data = json.loads(request.body)
        audit_id = data.get('audit_id')
        save_config = data.get('save_config', True)

        # Validar parámetros
        if not audit_id:
            return JsonResponse({
                'error': 'audit_id es requerido'
            }, status=400)

        # Verificar acceso a la auditoría
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse({
                'error': 'Auditoría no encontrada'
            }, status=404)

        # Validar configuración antes de generar
        validator = TemplateConfigValidator(audit_id)
        validation_result = validator.validate_full_configuration(data)

        if not validation_result['is_valid']:
            return JsonResponse({
                'error': 'Configuración inválida',
                'validation_errors': validation_result['errors']
            }, status=400)

        # Agregar información de auditoría a la configuración
        data['audit_info'] = {
            'title': audit.title,
            'created_by': request.user.get_full_name() or request.user.username
        }

        # Generar plantilla Excel
        logger.info(
            f"Generando plantilla para audit_id={audit_id}, "
            f"workbook_name={data.get('workbook_name')}"
        )

        generator = DynamicTemplateGenerator(data)
        excel_file = generator.generate()

        # Guardar configuración en base de datos (si se solicita)
        if save_config:
            template_config = TemplateConfiguration.objects.create(
                audit=audit,
                workbook_name=data['workbook_name'],
                created_by=request.user,
                configuration_json=data,
                download_count=1,
                last_downloaded_at=timezone.now()
            )

            # Guardar columnas
            for col_data in data['columns']:
                TemplateColumn.objects.create(
                    template_config=template_config,
                    column_name=col_data['name'],
                    column_order=col_data.get('order', 0),
                    column_width=col_data.get('width', 15),
                    data_type=col_data.get('data_type', 'text'),
                    is_required=col_data.get('is_required', False)
                )

            # Guardar símbolos seleccionados
            for idx, symbol_data in enumerate(data['symbols']):
                try:
                    symbol = SymbolLibrary.objects.get(
                        symbol=symbol_data['symbol'],
                        is_active=True
                    )
                    TemplateSymbol.objects.create(
                        template_config=template_config,
                        symbol=symbol,
                        display_order=idx
                    )
                except SymbolLibrary.DoesNotExist:
                    logger.warning(
                        f"Símbolo no encontrado: {symbol_data['symbol']}"
                    )

            logger.info(f"Configuración guardada: template_config_id={template_config.id}")

        # Preparar respuesta de descarga
        filename = generator.get_filename()

        response = HttpResponse(
            excel_file.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        logger.info(f"Plantilla generada exitosamente: {filename}")

        return response

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        logger.error(f"Error en generate_template: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}'
        }, status=500)


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5: Obtener Marcas de Auditoría Existentes
# ══════════════════════════════════════════════════════════════════════════════
@require_http_methods(["GET"])
@login_required
def get_audit_marks(request, audit_id):
    """
    GET /api/audit/{audit_id}/marks?include_inactive={bool}

    Obtiene las marcas de auditoría existentes para pre-poblar plantillas.

    Query Parameters:
    - include_inactive: bool (opcional, default=false)

    Response:
    {
        "marks": [{
            "id": int,
            "symbol": str,
            "description": str,
            "work_paper_number": str,
            "is_active": bool
        }],
        "total_count": int
    }
    """
    try:
        include_inactive = request.GET.get('include_inactive', 'false').lower() == 'true'

        # Verificar acceso a la auditoría
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            return JsonResponse({
                'error': 'Auditoría no encontrada'
            }, status=404)

        # Obtener marcas
        marks_query = AuditMark.objects.filter(audit=audit)

        if not include_inactive:
            marks_query = marks_query.filter(is_active=True)

        marks = marks_query.order_by('work_paper_number', 'created_at')

        # Serializar marcas
        marks_data = []

        for mark in marks:
            marks_data.append({
                'id': mark.id,
                'symbol': mark.symbol,
                'description': mark.description,
                'work_paper_number': mark.work_paper_number or '',
                'is_active': mark.is_active
            })

        response_data = {
            'marks': marks_data,
            'total_count': len(marks_data)
        }

        logger.debug(f"Marcas obtenidas para audit_id={audit_id}: {len(marks_data)}")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error en get_audit_marks: {e}", exc_info=True)
        return JsonResponse({
            'error': f'Error del servidor: {str(e)}'
        }, status=500)
