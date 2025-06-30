from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from audits.models import Audit
from django.contrib.auth.decorators import login_required

import os
import io
import urllib.parse
import json
import logging

from .word_utils import modify_document_word
from .excel_utils import modify_document_excel, modify_document_excel_with_macros
from .processors.shared.urls_programs import get_file_info_from_pattern

# Configurar logging
log_path = os.path.join(settings.BASE_DIR, 'logs')
if not os.path.exists(log_path):
    os.makedirs(log_path)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_path, 'auditoria.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def normalize_text(text):
    """
    Normaliza el texto removiendo tildes y caracteres especiales
    """
    import unicodedata    # Normalizar Unicode y remover tildes
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    # Convertir a minúsculas y remover espacios extras
    return ' '.join(text.lower().split())

def get_template_path(folder, filename, is_internal=False):
    """
    Obtiene la ruta completa de una plantilla
    """
    # Determinar qué carpeta base usar según el tipo de auditoría
    if is_internal:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
    else:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')
        
    if folder:
        # Normalizar la ruta usando os.path
        folder = folder.replace('/', os.path.sep).replace('\\', os.path.sep)
        current_path = base_path
        # Dividir la ruta usando el separador correcto del sistema
        folder_components = folder.split(os.path.sep)
        # Navegar por cada componente de la carpeta
        for component in folder_components:
            if component:
                current_path = os.path.join(current_path, component)
                if not os.path.exists(current_path):
                    # Buscar de forma case-insensitive y sin tildes
                    parent_dir = os.path.dirname(current_path)
                    if os.path.exists(parent_dir):
                        found = False
                        component_normalized = normalize_text(component)
                        for item in os.listdir(parent_dir):
                            if normalize_text(item) == component_normalized:
                                current_path = os.path.join(parent_dir, item)
                                found = True
                                break
                        if not found:
                            logger.info(f"No se encontró la carpeta: {component} en {parent_dir}")
                            return None
        if os.path.exists(current_path):
            # Primero intentar encontrar una coincidencia exacta
            exact_path = os.path.join(current_path, filename)
            if os.path.exists(exact_path):
                return exact_path
            # Si no hay coincidencia exacta, buscar de forma más flexible
            filename_normalized = normalize_text(filename)
            # Buscar recursivamente en la carpeta actual y subcarpetas
            for root, dirs, files in os.walk(current_path):
                for file in files:
                    # Comparar nombres normalizados (sin tildes y case insensitive)
                    if normalize_text(file) == filename_normalized:
                        return os.path.join(root, file)        
                    # Si aún no hay coincidencia, intentar comparar sin extensión
                    filename_base = os.path.splitext(filename_normalized)[0]
                    file_base = os.path.splitext(normalize_text(file))[0]
                    if file_base == filename_base:
                        return os.path.join(root, file)
    logger.info(f"No se encontró el archivo: {filename} en {folder if folder else base_path}")
    return None

@login_required
def download_document(request, audit_id, folder, filename):
    """Vista para descargar un documento específico"""
    # Decodificar la URL (por si tiene caracteres especiales)
    folder = urllib.parse.unquote(folder)
    filename = urllib.parse.unquote(filename)
    logger.info(f"Iniciando descarga de documento para auditoría {audit_id}")
    audit = get_object_or_404(Audit, id=audit_id)
    
    # Determinar si es auditoría interna
    is_internal = audit.tipoAuditoria == 'I'
    
    template_path = get_template_path(folder, filename, is_internal=is_internal)
    if not template_path or not os.path.exists(template_path):
        logger.error(f"Archivo no encontrado: {template_path}")
        return HttpResponse(f'Plantilla no encontrada: {folder}/{filename}', status=404)
    try:
        buffer = io.BytesIO()
        if filename.lower().endswith('.docx'):
            doc = modify_document_word(template_path, audit)
            doc.save(buffer)
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif filename.lower().endswith('.xlsx'):
            wb = modify_document_excel(template_path, audit)
            wb.save(buffer)
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif filename.lower().endswith('.xlsm'):
            # modify_document_excel_with_macros devuelve una ruta de archivo, no un objeto workbook
            processed_file_path = modify_document_excel_with_macros(template_path, audit)
            # Leer el contenido del archivo procesado en el buffer
            with open(processed_file_path, 'rb') as f:
                buffer.write(f.read())
            buffer.seek(0)
            content_type = 'application/vnd.ms-excel.sheet.macroEnabled.12'
        else:
            # Tipo no procesado, se devuelve el archivo tal cual
            return FileResponse(
                open(template_path, 'rb'),
                as_attachment=True,
                filename=os.path.basename(template_path)
            )

        buffer.seek(0)
        response = FileResponse(buffer, as_attachment=True, filename=os.path.basename(template_path))
        response['Content-Type'] = content_type

        logger.info("Documento procesado y enviado correctamente")
        return response

    except Exception as e:
        logger.error(f"Error al descargar documento: {str(e)}")
        logger.exception(e)
        return HttpResponse(f'Error al descargar documento: {str(e)}', status=500)

@login_required
def download_document_by_pattern(request, audit_id, pattern):
    """
    Vista para manejar hipervínculos generados en documentos Word.
    Recibe un ID de auditoría y un patrón (por ejemplo, 'A-1', 'R-10', etc.)
    y descarga el archivo correspondiente.
    
    Args:
        request: La solicitud HTTP
        audit_id: ID de la auditoría
        pattern: Patrón de nomenclatura (Ej: 'A-1', 'R-10')
        
    Returns:
        FileResponse: El archivo solicitado o un mensaje de error
    """
    try:
        logger.info(f"Solicitud de documento con patrón: audit_id={audit_id}, pattern={pattern}")
        
        # Verificar primero si la auditoría existe
        try:
            audit = Audit.objects.get(id=audit_id)
        except Audit.DoesNotExist:
            mensaje_error = crear_mensaje_error(
                "Auditoría no encontrada",
                f"La auditoría con ID {audit_id} no existe en el sistema."
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Verificar que el usuario tenga acceso a esta auditoría
        user_role = request.user.role.name
        has_access = False
        
        if user_role == "audit_manager" and audit.audit_manager == request.user:
            # Los administradores tienen acceso a las auditorías que crearon
            has_access = True
        elif user_role != "audit_manager" and audit.assigned_users.filter(id=request.user.id).exists():
            # Los auditores tienen acceso a las auditorías que les fueron asignadas
            has_access = True
        
        # Si no tiene acceso, mostrar mensaje de error
        if not has_access:
            mensaje_error = crear_mensaje_error(
                "Acceso restringido",
                "No tiene permisos para acceder a esta auditoría. Solo puede acceder a las auditorías que le han sido asignadas."
            )
            return HttpResponse(mark_safe(mensaje_error), status=403)
        
        # Determinar si es auditoría interna
        is_internal = audit.tipoAuditoria == 'I'
        
        # Obtener información del archivo a partir del patrón
        file_info = get_file_info_from_pattern(pattern, is_internal=is_internal)
        
        if not file_info:
            mensaje_error = crear_mensaje_error(
                "Archivo no encontrado",
                f"No se pudo encontrar el archivo correspondiente al patrón: <strong>{pattern}</strong><br>Por favor, verifique que el patrón sea correcto e intente nuevamente."
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Extraer la información del archivo
        folder = file_info['folder']
        filename = file_info['filename']
        template_path = file_info['full_path']
        
        # Verificar que el archivo existe
        if not os.path.exists(template_path):
            logger.error(f"Archivo no encontrado: {template_path}")
            mensaje_error = crear_mensaje_error(
                "Plantilla no encontrada",
                f"No se encontró la plantilla: {folder}/{filename}"
            )
            return HttpResponse(mark_safe(mensaje_error), status=404)
        
        # Procesar y devolver el documento
        try:
            buffer = io.BytesIO()
            if filename.lower().endswith('.docx'):
                doc = modify_document_word(template_path, audit)
                doc.save(buffer)
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif filename.lower().endswith('.xlsx'):
                wb = modify_document_excel(template_path, audit)
                wb.save(buffer)
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            else:
                # Tipo no procesado, se devuelve el archivo tal cual
                return FileResponse(
                    open(template_path, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(template_path)
                )

            buffer.seek(0)
            response = FileResponse(buffer, as_attachment=True, filename=os.path.basename(template_path))
            response['Content-Type'] = content_type

            logger.info(f"Documento {pattern} procesado y enviado correctamente")
            return response

        except Exception as e:
            logger.error(f"Error al procesar documento {pattern}: {str(e)}")
            logger.exception(e)
            mensaje_error = crear_mensaje_error(
                "Error al procesar documento",
                f"Ocurrió un error al procesar el documento {pattern}: {str(e)}"
            )
            return HttpResponse(mark_safe(mensaje_error), status=500)
        
    except Exception as e:
        logger.error(f"Error al procesar solicitud de documento con patrón: {str(e)}")
        logger.exception(e)
        mensaje_error = crear_mensaje_error(
            "Error en la solicitud",
            f"Ocurrió un error al procesar su solicitud: {str(e)}"
        )
        return HttpResponse(mark_safe(mensaje_error), status=500)

def crear_mensaje_error(titulo, mensaje):
    """
    Crea un mensaje de error HTML formateado.
    
    Args:
        titulo: Título del mensaje de error
        mensaje: Contenido del mensaje
        
    Returns:
        str: HTML formateado para mostrar el error
    """
    return f"""
    <html>
    <head>
        <title>{titulo}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            h1 {{ color: #e74c3c; }}
            .info {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; }}
            .button {{ 
                display: inline-block;
                background-color: #3498db;
                color: white;
                padding: 10px 15px;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 15px;
            }}
            .button:hover {{ background-color: #2980b9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>{titulo}</h1>
            <div class="info">
                <p>{mensaje}</p>
            </div>
            <a href="/auditoria/" class="button">Volver a auditorías</a>
        </div>
    </body>
    </html>
    """

def generar_html_estructura(estructura, audit_id, current_path='', user_verified=False):
    """
    Genera HTML recursivo para la estructura de carpetas.
    """ 
    if not estructura:
        return ""
    html = "<ul>"
    for nombre, contenido in estructura.items():
        if isinstance(contenido, dict):  # Es una carpeta
            # Usar os.path.join para construir la ruta
            new_path = os.path.join(current_path, nombre) if current_path else nombre
            # Convertir backslashes a forward slashes para la URL
            url_path = new_path.replace('\\', '/')
            # Generar un ID único y seguro para la carpeta
            escaped_path = new_path.replace('\\', '_')
            folder_id = f"folder_{urllib.parse.quote(escaped_path)}"
            html += f"""
            <li class="folder-item">
                <button class="folder-button" onclick="toggleFolder('{folder_id}')">
                    <img src="/static/icons/carpeta.svg" class="icon-img" alt="📂"/> {nombre}
                </button>
                <div id="{folder_id}" style="display: none;">
                    {generar_html_estructura(contenido, audit_id, new_path, user_verified)}
                </div>
            </li>
            """
        elif isinstance(contenido, list):  # Es un archivo
            if nombre.lower().endswith('.docx'):
                icono = '/static/icons/microsoft-word-2013-logo.svg'
                alt = '📝'
            elif nombre.lower().endswith(('.xlsx', '.xlsm')):
                icono = '/static/icons/microsoft-excel-2013.svg'
                alt = '📊'
            else:
                icono = '📄'
                alt = '📄'
                
            # Codificar la ruta y el nombre del archivo para la URL
            folder_encoded = urllib.parse.quote(current_path.replace('\\', '/')) if current_path else ''
            filename_encoded = urllib.parse.quote(nombre)
            download_url = f"/auditoria/download/{audit_id}/{folder_encoded}/{filename_encoded}"
            
            # aunque el usuario no esté verificado
            is_investment_folder = (current_path and 
                                     ("1 CAJA Y BANCOS" in current_path or 
                                      "3 INVERSIONES" in current_path or
                                      "2 AUDITORIA PROCESOS CONTABILIDAD" in current_path))
            
            # Mostrar con enlace si el usuario está verificado o si el archivo está en 3 INVERSIONES
            if user_verified or is_investment_folder:
                # Usuario verificado o archivo en carpeta de inversiones - muestra el enlace normalmente
                html += f"""
                <li class="file-item">
                    <a href="{download_url}" class="file-link">
                        <img src="{icono}" class="icon-img" alt="{alt}"/> {nombre}
                    </a>
                </li>"""
            else:
                # Usuario no verificado - muestra el archivo bloqueado
                html += f"""
                <li class="file-item file-locked">
                    <div class="file-link-disabled" style="display: flex; align-items: center; color: #999; cursor: not-allowed; position: relative; padding: 5px 8px; border-radius: 4px; background-color: rgba(0,0,0,0.03);" title="Usuario no verificado. Contacte al administrador para desbloquear el acceso.">
                        <img src="{icono}" class="icon-img" alt="{alt}" style="opacity: 0.5; margin-right: 5px;"/> 
                        <span style="margin-right: 25px;">{nombre}</span>
                        <i class="fas fa-lock" style="position: absolute; right: 10px; color: #e74c3c; font-size: 14px;"></i>
                    </div>
                </li>"""
    html += "</ul>"
    return html

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

    return render(request, 'auditoria/auditoria_financiera.html', {
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

    return render(request, 'auditoria/auditoria_interna.html', {
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
    except Exception as e:
        logger.error(f"Error al leer el archivo de estructura: {str(e)}")
        estructura_carpetas = {}  # Estructura vacía en caso de error
    
    # Usuario verificado si es administrador o tiene plan Mensual o Anual
    user_verified = request.user.username == 'administrador' or (hasattr(request.user, 'plan') and request.user.plan in ['M', 'A'])
    
    # Generar HTML de la estructura con la información de verificación
    estructura_html = generar_html_estructura(estructura_carpetas, audit_id, user_verified=user_verified)

    return render(request, 'auditoria/auditoria_detalle.html', {
        'audit': audit,
        'estructura_html': mark_safe(estructura_html),  # Para que Django no escape el HTML
        'user_verified': user_verified,  # Pasar esta variable a la plantilla para debug
    })