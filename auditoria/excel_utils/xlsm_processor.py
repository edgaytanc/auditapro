"""
Procesador principal para archivos Excel con macros (.xlsm).
Coordina entre xlwings y fallback de manipulación XML.
"""

import tempfile
import os
from .date_formatter import format_audit_dates
from .xlwings_handler import process_xlsm_with_xlwings, is_xlwings_available
from .shared_strings_replacer import replace_in_xlsm_shared_strings, build_filtered_replacements
from ..utils.replacements_utils import (
    get_replacements_config,
    build_replacements_dict,
)

def modify_document_excel_with_macros(template_path, audit):
    """
    Procesa archivos Excel con macros (.xlsm) manteniendo las macros intactas.
    Aplica solo los reemplazos básicos de texto usando xlwings o fallback XML.
    
    Args:
        template_path: Ruta al archivo XLSM original
        audit: Objeto Audit con los datos para reemplazar
        
    Returns:
        string: Ruta al archivo procesado (puede ser el mismo o un temporal)
    """
    if not is_xlwings_available():
        return _process_xlsm_fallback(template_path, audit)
    
    try:
        return _process_xlsm_with_xlwings(template_path, audit)
    except Exception:
        return template_path

def _process_xlsm_fallback(template_path: str, audit) -> str:
    """
    Procesa XLSM usando manipulación directa de XML como fallback.
    """
    try:
        # Preparar fechas
        fecha_inicio, fecha_fin = format_audit_dates(audit)
        
        # Construir reemplazos
        replacements_config = get_replacements_config()
        replacements_all = build_replacements_dict(
            config=replacements_config,
            audit=audit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        
        # Filtrar reemplazos para XLSM
        filtered_repl = build_filtered_replacements(replacements_all)
        
        # Crear archivo temporal destino (mismo nombre)
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, os.path.basename(template_path))
        
        replace_in_xlsm_shared_strings(template_path, temp_file_path, filtered_repl)
        return temp_file_path
        
    except Exception:
        return template_path

def _process_xlsm_with_xlwings(template_path: str, audit) -> str:
    """
    Procesa XLSM usando xlwings para preservar macros completamente.
    """
    # Preparar los datos para reemplazos
    fecha_inicio, fecha_fin = format_audit_dates(audit)
    
    # Obtener la configuración de reemplazos
    replacements_config = get_replacements_config()
    
    # Construir el diccionario de reemplazos usando la misma función que modify_document_excel
    replacements = build_replacements_dict(
        config=replacements_config,
        audit=audit,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    
    return process_xlsm_with_xlwings(template_path, replacements)
