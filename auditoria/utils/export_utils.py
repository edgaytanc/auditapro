import os
import io
from django.conf import settings
import openpyxl
from django.http import FileResponse, HttpResponse
from audits.models import Audit
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required
def export_cuentas_contables(request, audit_id, tipo):
    """
    Exporta el archivo de estados financieros.
    
    Args:
        request: La solicitud HTTP
        audit_id: ID de la auditoría
        tipo: Tipo de exportación (parámetro mantenido por compatibilidad)
    
    Returns:
        FileResponse: El archivo Excel descargable
    """
    audit = get_object_or_404(Audit, id=audit_id)

    # Nombre de la plantilla (ahora usamos un único archivo)
    filename_template = 'ESTADOS-FINANCIEROS.xlsx'
    template_path = os.path.join(settings.BASE_DIR, 'static', 'template-est-fin', filename_template)

    if not os.path.exists(template_path):
        return HttpResponse(f"No se encontró la plantilla '{filename_template}'.", status=404)

    # Cargar y preparar el archivo
    wb = openpyxl.load_workbook(template_path)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Generar nombre de descarga usando el ID de la auditoría
    download_name = f"ESTADOS-FINANCIEROS-{audit.id}.xlsx"
    response = FileResponse(buffer, as_attachment=True, filename=download_name)
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    
    return response