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
from auditoria.services import muestreo_datos

logger = logging.getLogger(__name__)

# El cliente confirmó que este módulo se descarga SOLO en Excel.
CONTENT_TYPES = {
    'excel': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

# Clave de sesión donde queda la última muestra generada desde un Excel de
# datos. Guarda ÚNICAMENTE las partidas seleccionadas: el archivo subido se
# procesa en memoria y se descarta al terminar la petición, nunca se almacena.
CLAVE_SESION_DETALLE = 'muestreo_detalle'

TAMANO_MAXIMO_MB = 10


def _clave_parametros(parametros):
    """
    Parámetros que identifican la muestra, sin el detalle transaccional.

    En 'Por Criterio' el auditor puede pegar miles de partidas: esas no viajan
    en la URL de descarga, así que tampoco forman parte de la clave con la que
    se reconoce la muestra guardada en la sesión.
    """
    return {clave: valor for clave, valor in (parametros or {}).items()
            if clave != 'partidas'}


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
    """
    Página del módulo de Muestreo NIA 530.

    Es el HTML que entregó el cliente (Monetario MUM, Por Atributos y Por
    Criterio), integrado tal cual: el cálculo, la memoria de cálculo, la
    importación del detalle transaccional y la descarga de la muestra en Excel
    funcionan dentro de la propia página.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error
    return render(request, 'auditoria/muestreo/muestreo_nia530_cliente.html', {
        'audit': audit,
        'nombre_auditoria': f"{audit.title} - {audit.identidad}",
    })


@login_required
def muestreo_page_motor(request, audit_id):
    """
    Página anterior del muestreo (motor del servidor con los 5 métodos).

    Se conserva accesible porque genera el papel de trabajo en Excel desde el
    servidor; la página principal es la que entregó el cliente.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error
    return render(request, 'auditoria/muestreo/muestreo.html', {
        'audit': audit,
        'nombre_auditoria': f"{audit.title} - {audit.identidad}",
    })


@login_required
def muestreo_mum(request, audit_id):
    """
    Página de Muestreo MUM (NIA 530) con el HTML que entregó el cliente.

    Se integró tal cual: el cálculo, la memoria de cálculo, la importación del
    detalle transaccional y la descarga de la muestra en Excel funcionan dentro
    de la propia página. Solo se sustituyeron los dos datos del encabezado por
    los de la auditoría real.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error
    return render(request, 'auditoria/muestreo/muestreo_mum.html', {'audit': audit})


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

    # En 'Por Criterio' el detalle pegado no viaja en la URL de descarga, así
    # que la muestra calculada se guarda para que el Excel salga igual que en
    # pantalla sin volver a pedir las partidas.
    if metodo == 'criterio':
        detalle = muestreo_datos.mapear_seleccion_a_partidas(
            resultado, parametros.get('partidas') or [])
        if detalle:
            resultado['detalle_partidas'] = detalle
        request.session[CLAVE_SESION_DETALLE] = {
            'audit_id': audit.id,
            'metodo': metodo,
            'parametros': _clave_parametros(parametros),
            'resultado': resultado,
        }
        request.session.modified = True

    return JsonResponse({'success': True, 'data': resultado})


@login_required
def muestreo_importar_datos(request, audit_id):
    """
    Importa el Excel de datos (mayor auxiliar) y genera la muestra.

    El archivo NO se guarda en el sistema: se lee en memoria, se derivan los
    parámetros de la población (N, σ, valor en libros), se calcula la muestra y
    se descarta. En la sesión solo quedan las partidas seleccionadas, para que
    la descarga en Excel las incluya sin volver a subir el archivo.

    POST multipart con:
      - archivo_datos: el Excel del mayor auxiliar
      - metodo: clave del método de muestreo
      - parametros: JSON con los parámetros del método (los derivables del
        archivo pueden venir vacíos: se completan con los del archivo)
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return JsonResponse(
            {'success': False, 'error': 'Acceso no autorizado a la auditoría.'},
            status=error.status_code,
        )

    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Método HTTP no permitido. Use POST.'}, status=405)

    archivo = request.FILES.get('archivo_datos')
    if not archivo:
        return JsonResponse(
            {'success': False, 'error': 'No se adjuntó ningún archivo Excel de datos.'},
            status=400,
        )
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        return JsonResponse(
            {'success': False,
             'error': f'El archivo supera los {TAMANO_MAXIMO_MB} MB permitidos.'},
            status=400,
        )

    try:
        datos_archivo = muestreo_datos.parsear_mayor_auxiliar(archivo)
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error leyendo el Excel de datos (auditoría {audit_id}): {e}")
        return JsonResponse(
            {'success': False, 'error': 'No se pudo leer el archivo Excel de datos.'},
            status=400,
        )
    finally:
        # El archivo se descarta explícitamente: no se escribe en disco ni en BD
        archivo.close()

    metodo = request.POST.get('metodo') or 'aleatorio_simple'
    try:
        parametros = json.loads(request.POST.get('parametros') or '{}')
    except json.JSONDecodeError:
        return JsonResponse(
            {'success': False, 'error': "El campo 'parametros' debe ser JSON válido."},
            status=400,
        )
    if not isinstance(parametros, dict):
        return JsonResponse(
            {'success': False, 'error': "El campo 'parametros' debe ser un objeto JSON."},
            status=400,
        )

    parametros = muestreo_datos.completar_parametros(metodo, parametros, datos_archivo)

    try:
        # MUS y Por Criterio seleccionan partidas REALES: necesitan el detalle
        resultado = muestreo_nia530.calcular_muestreo(
            metodo, parametros, audit_id=audit.id,
            partidas=datos_archivo['partidas'],
        )
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error calculando la muestra importada (auditoría {audit_id}): {e}")
        return JsonResponse(
            {'success': False, 'error': 'Error inesperado al calcular la muestra.'}, status=500)

    try:
        detalle = muestreo_datos.mapear_seleccion_a_partidas(
            resultado, datos_archivo['partidas'])
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    if detalle:
        resultado['detalle_partidas'] = detalle

    # Se guarda la muestra tal como se calculó, para que el Excel descargado sea
    # EXACTAMENTE el que el auditor vio en pantalla (evidencia reproducible).
    # El archivo subido no se guarda: solo este resultado.
    request.session[CLAVE_SESION_DETALLE] = {
        'audit_id': audit.id,
        'metodo': metodo,
        'parametros': _clave_parametros(parametros),
        'resultado': resultado,
    }
    request.session.modified = True

    return JsonResponse({
        'success': True,
        'data': resultado,
        'origen': {
            'archivo': archivo.name,
            'empresa': datos_archivo['empresa'],
            'cuenta': datos_archivo['cuenta'],
            'partidas': datos_archivo['n'],
            'valor_libros': datos_archivo['bv'],
            'desviacion_estandar': datos_archivo['sigma'],
        },
        'parametros_aplicados': parametros,
        'mensaje': (
            f"Se leyeron {datos_archivo['n']:,} partidas y se generó la muestra. "
            "El archivo no se almacenó en el sistema."
        ),
    })


@login_required
def muestreo_formato_datos(request, audit_id):
    """Descarga el Excel de ejemplo con la estructura que espera el módulo."""
    _audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error

    contenido = muestreo_datos.generar_formato_ejemplo()
    respuesta = FileResponse(
        io.BytesIO(contenido), as_attachment=True,
        filename='Formato_Mayor_Auxiliar_Muestreo.xlsx',
    )
    respuesta['Content-Type'] = CONTENT_TYPES['excel']
    return respuesta


@login_required
def muestreo_descargar(request, audit_id):
    """
    Descarga el papel de trabajo generado, siempre en Excel.

    GET con los mismos parámetros del cálculo:
      - metodo: clave del método
      - parametros: JSON con los parámetros del método

    Si la muestra se generó desde un Excel de datos importado, la hoja
    'Selección' incluye las partidas reales guardadas en la sesión.
    """
    audit, error = _obtener_auditoria(request, audit_id)
    if error:
        return error

    formato = (request.GET.get('formato') or 'excel').lower()
    if formato not in CONTENT_TYPES:
        return JsonResponse(
            {'success': False,
             'error': f"Formato no soportado: {formato}. Este módulo se descarga en Excel."},
            status=400,
        )

    metodo = request.GET.get('metodo')
    try:
        parametros = json.loads(request.GET.get('parametros') or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': "El parámetro 'parametros' debe ser JSON válido."}, status=400)
    if not isinstance(parametros, dict):
        return JsonResponse({'success': False, 'error': "El parámetro 'parametros' debe ser un objeto JSON."}, status=400)

    # Si la muestra se generó desde un Excel de datos, se descarga EXACTAMENTE
    # la que se calculó entonces (misma auditoría, método y parámetros): así el
    # papel de trabajo coincide con lo que el auditor vio, sin recalcular.
    guardado = request.session.get(CLAVE_SESION_DETALLE)
    reutilizable = (
        guardado
        and guardado.get('audit_id') == audit.id
        and guardado.get('metodo') == metodo
        and guardado.get('parametros') == _clave_parametros(parametros)
    )

    resultado = None
    if reutilizable and guardado.get('resultado'):
        resultado = guardado['resultado']

    if resultado is None:
        try:
            resultado = muestreo_nia530.calcular_muestreo(
                metodo, parametros, audit_id=audit.id)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        # Compatibilidad con muestras guardadas por la versión anterior
        if reutilizable and guardado.get('detalle'):
            resultado['detalle_partidas'] = guardado['detalle']

    info = _info_auditoria(audit)

    try:
        contenido = muestreo_export.generar_excel(info, resultado)
    except Exception as e:
        logger.error(f"Error generando el archivo de muestreo (auditoría {audit_id}): {e}")
        return HttpResponse(f'Error al generar el documento: {str(e)}', status=500)

    nombre = muestreo_export.nombre_archivo(resultado, audit.id, 'xlsx')

    respuesta = FileResponse(io.BytesIO(contenido), as_attachment=True, filename=nombre)
    respuesta['Content-Type'] = CONTENT_TYPES['excel']
    return respuesta
