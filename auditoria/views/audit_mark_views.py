"""
Vistas para el sistema de marcas de auditoría
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse, Http404
from django.conf import settings
from audits.models import Audit
from auditoria.services.audit_mark_import_service import AuditMarkImportService
import os


def _user_has_audit_access(user, audit):
    """Verifica si el usuario puede acceder a esta auditoría."""
    if hasattr(user, 'role') and user.role and user.role.name == 'audit_manager':
        return audit.audit_manager == user
    return audit.assigned_users.filter(id=user.id).exists()


@login_required
def upload_audit_marks(request, audit_id):
    """Maneja la carga de archivo Excel con marcas de auditoría."""
    audit = get_object_or_404(Audit, id=audit_id)

    if not _user_has_audit_access(request.user, audit):
        return JsonResponse({'error': 'Acceso denegado'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    if 'excel_file' not in request.FILES:
        return JsonResponse({'error': 'No se cargó ningún archivo'}, status=400)

    try:
        excel_file = request.FILES['excel_file']
        replace_existing = request.POST.get('replace_existing') == 'on'

        service = AuditMarkImportService(audit_id, excel_file)
        result = service.import_marks(replace_existing=replace_existing)

        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def download_audit_mark_template(request):
    """Descarga la plantilla MODELO de marcas de auditoría."""
    modelo_path = os.path.join(
        settings.BASE_DIR,
        'MODELO DE MARCAS_DE_AUDITORIA_VINCULADO.xlsx'
    )

    if not os.path.exists(modelo_path):
        raise Http404("Plantilla de marcas no encontrada.")

    try:
        with open(modelo_path, 'rb') as excel_file:
            response = HttpResponse(
                excel_file.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="MODELO_MARCAS_AUDITORIA.xlsx"'
            return response
    except Exception:
        raise Http404("Error al descargar plantilla.")
