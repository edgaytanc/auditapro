"""
Vistas para gestión de auditorías.
Contiene funciones para listar auditorías financieras, internas y mostrar detalles.
"""

import os
import json
from .config import (
    render, redirect, HttpResponse, mark_safe, settings,
    Audit, login_required
)
from .utils import crear_mensaje_error, generar_html_estructura

@login_required
def auditorias_view(request):
    return render(request, 'auditoria/auditorias.html', {})

@login_required
def auditoria_financiera_view(request):
    user_role = request.user.role.name
    
    # Filtrado según el rol del usuario
    if user_role == "audit_manager":
        # Los administradores ven todas las auditorías que crearon
        auditorias_financieras = Audit.objects.filter(audit_manager=request.user, tipoAuditoria='F')
    else:
        # Los auditores regulares solo ven las auditorías asignadas a ellos
        auditorias_financieras = Audit.objects.filter(assigned_users=request.user, tipoAuditoria='F')
    
    if request.method == 'POST':
        audit_id = request.POST.get('audit_id')
        return redirect('auditoria_detalle', audit_id=audit_id)

    return render(request, 'auditoria/auditoria-financiera/auditoria_financiera.html', {
        'auditorias': auditorias_financieras
    })

@login_required
def auditoria_interna_view(request):
    user_role = request.user.role.name
    
    # Filtrado según el rol del usuario
    if user_role == "audit_manager":
        # Los administradores ven todas las auditorías que crearon
        auditorias_internas = Audit.objects.filter(audit_manager=request.user, tipoAuditoria='I')
    else:
        # Los auditores regulares solo ven las auditorías asignadas a ellos
        auditorias_internas = Audit.objects.filter(assigned_users=request.user, tipoAuditoria='I')
     
    if request.method == 'POST':
        audit_id = request.POST.get('audit_id')
        return redirect('auditoria_detalle', audit_id=audit_id)

    return render(request, 'auditoria/auditoria-interna/auditoria_interna.html', {
        'auditorias': auditorias_internas
    })

@login_required
def auditoria_detalle_view(request, audit_id):
    user_role = request.user.role.name
    
    # Verificar primero si la auditoría existe
    try:
        if user_role == "audit_manager":
            # Los administradores solo pueden ver auditorías que ellos crearon
            audit = Audit.objects.get(id=audit_id, audit_manager=request.user)
        else:
            # Los auditores regulares solo pueden ver auditorías asignadas a ellos
            audit = Audit.objects.get(id=audit_id, assigned_users=request.user)
    except Audit.DoesNotExist:
        mensaje_error = crear_mensaje_error(
            "Auditoría no encontrada",
            "La auditoría solicitada no existe o no tienes permisos para acceder a ella."
        )
        return HttpResponse(mark_safe(mensaje_error), status=404)
    
    # Leer la estructura desde el archivo JSON correspondiente al tipo de auditoría
    if audit.tipoAuditoria == 'I':
        json_path = os.path.join(settings.BASE_DIR, 'auditoria', 'config', 'folder_structure_interna.json')
    else:
        json_path = os.path.join(settings.BASE_DIR, 'auditoria', 'config', 'folder_structure_financiera.json')
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            estructura_carpetas = json.load(f)
    except Exception:
        estructura_carpetas = {}  # Estructura vacía en caso de error
    
    # Usuario verificado si es administrador o tiene plan Mensual o Anual
    user_verified = request.user.username == 'administrador' or (hasattr(request.user, 'plan') and request.user.plan in ['M', 'A'])
    
    # Generar HTML de la estructura con la información de verificación
    estructura_html = generar_html_estructura(estructura_carpetas, audit_id, user_verified=user_verified)

    return render(request, 'auditoria/auditoria-detalle/auditoria_detalle.html', {
        'audit': audit,
        'estructura_html': mark_safe(estructura_html),  # Para que Django no escape el HTML
        'user_verified': user_verified,  # Pasar esta variable a la plantilla para debug
    })
