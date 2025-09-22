"""
Módulo para mapear patrones de hipervínculos a rutas de archivos.
Proporciona funciones para convertir patrones como 'A-1', 'R-10' a rutas de archivos reales.
"""

import os
import logging
import json
from django.conf import settings

from .financial_audit_mappings import PREFIX_TO_FOLDER, PATTERN_TO_FILE
from .internal_audit_mappings import INTERNAL_PREFIX_TO_FOLDER, INTERNAL_PATTERN_TO_FILE, INTERNAL_PREFIX_TO_PROGRAM
from .special_patterns import SPECIAL_PATTERNS, PREFIX_TO_PROGRAM

logger = logging.getLogger(__name__)

def get_file_info_from_pattern(pattern, is_internal=False):
    """
    Convierte un patrón (ej: 'A-1', 'R-10') en información necesaria para descargar el archivo.
    
    Args:
        pattern: El patrón de nomenclatura (ej: 'A-1')
        is_internal: Si es True, se busca en templates_base_interna, si no, en templates_base_financiera
        
    Returns:
        dict: Diccionario con la información del archivo o None si no se encuentra
            {
                'folder': Carpeta relativa donde se encuentra el archivo,
                'filename': Nombre del archivo,
                'full_path': Ruta completa del archivo en el sistema de archivos
            }
    """
    if not pattern or '-' not in pattern:
        logger.warning(f"Patrón inválido: {pattern}")
        return None
        
    # Extraer el prefijo (A, B, R, etc.)
    prefix = pattern.split('-')[0]
    
    # Obtener la carpeta base y el patrón según el tipo de auditoría
    if is_internal:
        folder = INTERNAL_PREFIX_TO_FOLDER.get(prefix)
        pattern_to_file = INTERNAL_PATTERN_TO_FILE
        prefix_to_program = INTERNAL_PREFIX_TO_PROGRAM
    else:
        folder = PREFIX_TO_FOLDER.get(prefix)
        pattern_to_file = PATTERN_TO_FILE
        prefix_to_program = PREFIX_TO_PROGRAM
    
    if not folder:
        logger.warning(f"Prefijo no reconocido: {prefix} para {'auditoría interna' if is_internal else 'auditoría financiera'}")
        return None
    
    # Verificar si es un patrón especial
    if pattern in SPECIAL_PATTERNS:
        filename = SPECIAL_PATTERNS[pattern]
    else:
        # Obtener el nombre del archivo para este patrón
        filename = pattern_to_file.get(pattern)
    
    if not filename:
        # Caso especial: si no se encuentra el patrón, podría estar buscando el programa
        if pattern.split('-')[1].lower() == 'programa' or (prefix in 'ABCDEFGHIJR' and pattern not in pattern_to_file):
            filename = prefix_to_program.get(prefix)
            logger.info(f"Usando el programa principal para el patrón: {pattern}")
        else:
            logger.warning(f"No se encontró archivo para el patrón: {pattern}")
            return None
    
    # Construir la ruta completa según el tipo de auditoría
    if is_internal:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
    else:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')
    
    full_path = os.path.join(base_path, folder, filename)
    
    # Verificar si el archivo existe
    if not os.path.exists(full_path):
        logger.warning(f"El archivo no existe en la ruta: {full_path}")
        # Intentar buscar el archivo de forma más flexible
        from auditoria.views import normalize_text, get_template_path
        template_path = get_template_path(folder, filename, is_internal=is_internal)
        if template_path:
            full_path = template_path
        else:
            logger.error(f"No se pudo encontrar el archivo para el patrón: {pattern}")
            return None
    
    return {
        'folder': folder,
        'filename': filename,
        'full_path': full_path
    }

# def get_pattern_from_file(folder, filename):
#     """
#     Función inversa que obtiene el patrón a partir de la carpeta y nombre de archivo.
    
#     Args:
#         folder: Carpeta relativa donde se encuentra el archivo
#         filename: Nombre del archivo
        
#     Returns:
#         str: El patrón correspondiente o None si no se encuentra
#     """
#     # Verificar si es un archivo especial primero
#     for pattern, fname in SPECIAL_PATTERNS.items():
#         if fname == filename:
#             return pattern
    
#     # Determinar si es auditoría interna o financiera
#     is_internal = '6 auditoria de procesos' in folder.lower()
    
#     # Determinar el prefijo basado en la carpeta
#     prefix = None
    
#     if is_internal:
#         prefix_to_folder = INTERNAL_PREFIX_TO_FOLDER
#         pattern_to_file = INTERNAL_PATTERN_TO_FILE
#         prefix_to_program = INTERNAL_PREFIX_TO_PROGRAM
#     else:
#         prefix_to_folder = PREFIX_TO_FOLDER
#         pattern_to_file = PATTERN_TO_FILE
#         prefix_to_program = PREFIX_TO_PROGRAM
    
#     for p, f in prefix_to_folder.items():
#         if f.lower() in folder.lower():
#             prefix = p
#             break
    
#     if not prefix:
#         logger.warning(f"No se pudo determinar el prefijo para la carpeta: {folder}")
#         return None
    
#     # Buscar el patrón que corresponde a este archivo
#     for pattern, file in pattern_to_file.items():
#         if file == filename and pattern.startswith(prefix):
#             return pattern
    
#     # Caso especial para el programa principal
#     if filename == prefix_to_program.get(prefix):
#         return f"{prefix}-programa"  # Devolver un código especial para el programa
    
#     logger.warning(f"No se encontró patrón para el archivo: {folder}/{filename}")
#     return None
