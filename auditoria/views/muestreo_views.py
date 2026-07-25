"""
Vistas del módulo de Muestreo NIA 530.

Sustituye a la antigua carpeta estática '4 MUESTREO': el auditor define los
parámetros, el sistema calcula el tamaño de muestra y la selección de
elementos, y genera el papel de trabajo en Excel, Word o PDF.
"""

import io
import json
import logging

from .config import (
    render, HttpResponse, JsonResponse, FileResponse,
    mark_safe, Audit, login_required,
)
from .utils import crear_mensaje_error
from auditoria.services import muestreo_nia530
from auditoria.services import muestreo_export

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'word': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'pdf': 'application/pdf',
}


def _verificar_acceso(request, audit):
    """
    Verifica que el usuario tenga acceso a la auditoría (mismo patrón que
    download_document_by_pattern): el jefe accede a las auditorías que creó y
    los auditores a las que les fueron asignadas.
    """
    user_role = request.user.role.name
    if user_role == "audit_manager" and audit.audit_manager == request.user:
        return True
    if user_role != "audit_manager" and audit.assigned_users.filter(id=request.user.id).exists():
        return True
    return False


def _obtener_auditoria(request, audit_id):
    """Devuelve (audit, None) o (None, respuesta de error) según acceso."""
    try:
        audit = Audit.objects.get(id=audit_id)
    except Audit.DoesNotExist:
        mensaje_error = crear_mensaje_error(
            "Auditoría no encontrada",
            f"La auditoría con ID {audit_id} no existe en el sistema."
        )
        return None, HttpResponse(mark_safe(mensaje_error), status=404)

    if not _verificar_acceso(request, audit):
        mensaje_error = crear_mensaje_error(
            "Acceso restringido",
            "No tiene permisos para acceder a esta auditoría. Solo puede acceder a las auditorías que le han sido asignadas."
        )
        return None, HttpResponse(mark_safe(mensaje_error), status=403)
    return audit, None


def _info_auditoria(audit):
    """Arma el diccionario de encabezado que usan los generadores de archivos."""
    return {
        'entidad': audit.identidad,
        'titulo': audit.title,
        'periodo': f"{audit.fechaInit.strftime('%d/%m/%Y')} — {audit.fechaEnd.strftime('%d/%m/%Y')}",
        'audit_id': audit.id,
        'moneda': audit.moneda,
    }


@login_required
def muestreo_page(request, audit_id):
    """Página del módulo de muestreo: formulario de parámetros por método."""
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error
    return render(request, 'auditoria/muestreo/muestreo.html', {
        'audit': audit,
        'nombre_auditoria': f"{audit.title} - {audit.identidad}",
    })


@login_required
def muestreo_calcular(request, audit_id):
    """
    Calcula el tamaño de muestra y la selección de elementos.

    Espera un POST con cuerpo JSON: {'metodo': str, 'parametros': {...}}.
    Devuelve el diccionario del servicio más una bandera de éxito.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return JsonResponse({'success': False, 'error': 'Acceso no autorizado a la auditoría.'}, status=error.status_code)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método HTTP no permitido. Use POST.'}, status=405)

    try:
        cuerpo = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Cuerpo de la solicitud inválido: se esperaba JSON.'}, status=400)

    if not isinstance(cuerpo, dict):
        return JsonResponse({'success': False, 'error': 'Cuerpo de la solicitud inválido: se esperaba un objeto JSON.'}, status=400)

    metodo = cuerpo.get('metodo')
    parametros = cuerpo.get('parametros') or {}
    if not isinstance(parametros, dict):
        return JsonResponse({'success': False, 'error': "El campo 'parametros' debe ser un objeto JSON."}, status=400)

    try:
        resultado = muestreo_nia530.calcular_muestreo(metodo, parametros, audit_id=audit.id)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en muestreo_calcular (auditoría {audit_id}): {e}")
        return JsonResponse({'success': False, 'error': 'Error inesperado al calcular la muestra.'}, status=500)

    return JsonResponse({'success': True, 'data': resultado})


@login_required
def muestreo_descargar(request, audit_id):
    """
    Descarga el papel de trabajo generado.

    GET con los mismos parámetros del cálculo:
      - metodo: clave del método
      - parametros: JSON con los parámetros del método
      - formato: excel | word | pdf

    Si se pide PDF y weasyprint no está disponible (entorno local), se entrega
    el Excel como alternativa con el encabezado 'X-Muestreo-Advertencia'.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error

    formato = (request.GET.get('formato') or 'excel').lower()
    if formato not in CONTENT_TYPES:
        return JsonResponse({'success': False, 'error': f"Formato no soportado: {formato}. Use excel, word o pdf."}, status=400)

    metodo = request.GET.get('metodo')
    try:
        parametros = json.loads(request.GET.get('parametros') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': "El parámetro 'parametros' debe ser JSON válido."}, status=400)
    if not isinstance(parametros, dict):
        return JsonResponse({'success': False, 'error': "El parámetro 'parametros' debe ser un objeto JSON."}, status=400)

    try:
        resultado = muestreo_nia530.calcular_muestreo(metodo, parametros, audit_id=audit.id)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    info = _info_auditoria(audit)
    advertencia = None

    try:
        if formato == 'excel':
            contenido = muestreo_export.generar_excel(info, resultado)
        elif formato == 'word':
            contenido = muestreo_export.generar_word(info, resultado)
        else:  # pdf
            contenido = muestreo_export.generar_pdf(info, resultado)
            if contenido is None:
                # weasyprint no disponible: entregar el Excel como alternativa
                advertencia = (
                    "Generación de PDF no disponible en este entorno; "
                    "se entrega el papel de trabajo en Excel."
                )
                logger.warning(f"weasyprint no disponible para la auditoría {audit_id}: {advertencia}")
                formato = 'excel'
                contenido = muestreo_export.generar_excel(info, resultado)
    except Exception as e:
        logger.error(f"Error generando el archivo de muestreo (auditoría {audit_id}): {e}")
        return HttpResponse(f'Error al generar el documento: {str(e)}', status=500)

    extension = {'excel': 'xlsx', 'word': 'docx', 'pdf': 'pdf'}[formato]
    nombre = muestreo_export.nombre_archivo(resultado, audit.id, extension)

    respuesta = FileResponse(io.BytesIO(contenido), as_attachment=True, filename=nombre)
    respuesta['Content-Type'] = CONTENT_TYPES[formato]
    if advertencia:
        respuesta['X-Muestreo-Advertencia'] = advertencia
    return respuesta
