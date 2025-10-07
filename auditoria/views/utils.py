"""
Utilidades y funciones helper para las vistas de auditoría.
Contiene funciones de normalización, rutas, mensajes de error y generación de HTML.
"""

import os
import urllib.parse
import unicodedata
from django.conf import settings

def normalize_text(text):
    """
    Normaliza el texto removiendo tildes y caracteres especiales
    """
    # Normalizar Unicode y remover tildes
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
    return None

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
