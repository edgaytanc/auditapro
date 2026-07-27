"""
Vistas de los parámetros editables de la auditoría.

Cubren las dos consultas del cliente:

  · Años (actual / anterior) de los cuadros comparativos: se llenan solos al
    importar el Excel Financiero y el auditor puede corregirlos aquí.
  · Referencia (Ref.) de cada papel de trabajo: el sistema la calcula desde el
    índice maestro, pero el auditor puede fijar la suya y el sistema NO se la
    sobrescribe; es la que se pega en la plantilla al descargarla.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from audits.models import Audit
from auditoria.models import ReferenciaPapelTrabajo
from auditoria.services.parametros_anios import (
    anios_de_auditoria,
    guardar_anios_manuales,
    obtener_parametros,
)
from auditoria.services.referencias import ref_automatica, ref_manual


def _cuerpo(request):
    """Lee el cuerpo de la petición como dict, venga en JSON o como formulario."""
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body or b'{}')
        except json.JSONDecodeError:
            return {}
    return request.POST.dict()


def _auditoria_accesible(request, audit_id):
    """La auditoría solo es accesible para su jefe o los auditores asignados."""
    audit = get_object_or_404(Audit, id=audit_id)
    if audit.audit_manager_id == request.user.id:
        return audit
    if audit.assigned_users.filter(id=request.user.id).exists():
        return audit
    return None


# ---------------------------------------------------------------------
# Años de la auditoría
# ---------------------------------------------------------------------

@login_required
@require_http_methods(['GET', 'POST'])
def anios_auditoria(request, audit_id):
    """Consulta (GET) o guarda (POST) los años de los cuadros comparativos."""
    audit = _auditoria_accesible(request, audit_id)
    if audit is None:
        return JsonResponse(
            {'success': False, 'message': 'No tiene acceso a esta auditoría.'}, status=403
        )

    if request.method == 'GET':
        parametros = obtener_parametros(audit_id)
        return JsonResponse({
            'success': True,
            'anio_actual': parametros.anio_actual,
            'anio_anterior': parametros.anio_anterior,
            'manuales': parametros.anios_manuales,
        })

    datos = _cuerpo(request)
    try:
        anio_actual, anio_anterior = guardar_anios_manuales(
            audit_id, datos.get('anio_actual'), datos.get('anio_anterior')
        )
    except ValueError as error:
        return JsonResponse({'success': False, 'message': str(error)}, status=400)

    return JsonResponse({
        'success': True,
        'message': 'Años actualizados. Se aplicarán en las plantillas que descargue.',
        'anio_actual': anio_actual,
        'anio_anterior': anio_anterior,
        'manuales': True,
    })


# ---------------------------------------------------------------------
# Referencia de un papel de trabajo
# ---------------------------------------------------------------------

@login_required
@require_http_methods(['POST'])
def referencia_papel(request, audit_id):
    """
    Fija o restablece la referencia de un papel de trabajo.

    Cuerpo esperado: {carpeta, archivo, referencia}. Una `referencia` vacía
    borra la personalización y devuelve el papel a la referencia automática.
    """
    audit = _auditoria_accesible(request, audit_id)
    if audit is None:
        return JsonResponse(
            {'success': False, 'message': 'No tiene acceso a esta auditoría.'}, status=403
        )

    datos = _cuerpo(request)
    carpeta = (datos.get('carpeta') or '').replace('\\', '/').strip('/')
    archivo = (datos.get('archivo') or '').strip()
    referencia = (datos.get('referencia') or '').strip()

    if not archivo:
        return JsonResponse(
            {'success': False, 'message': 'Falta el papel de trabajo.'}, status=400
        )

    automatica = ref_automatica(audit.tipoAuditoria, carpeta, archivo)

    # Vacío o igual a la automática: se elimina la personalización
    if not referencia or referencia == automatica:
        ReferenciaPapelTrabajo.objects.filter(
            audit_id=audit_id, carpeta=carpeta, archivo=archivo
        ).delete()
        return JsonResponse({
            'success': True,
            'referencia': automatica,
            'manual': False,
            'message': 'Se restableció la referencia automática.',
        })

    if len(referencia) > 50:
        return JsonResponse(
            {'success': False, 'message': 'La referencia no puede superar 50 caracteres.'},
            status=400,
        )

    ReferenciaPapelTrabajo.objects.update_or_create(
        audit_id=audit_id, carpeta=carpeta, archivo=archivo,
        defaults={'referencia': referencia},
    )

    return JsonResponse({
        'success': True,
        'referencia': referencia,
        'manual': True,
        'message': 'Referencia guardada. Se pegará así en la plantilla al descargarla.',
    })
