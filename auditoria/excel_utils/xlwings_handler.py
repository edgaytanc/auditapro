"""
Manejador de xlwings para procesamiento de archivos Excel con macros.
Contiene funciones para aplicar reemplazos usando xlwings preservando macros.
"""

import logging
import tempfile
import os
import shutil

try:
    import xlwings as xw
except ImportError:
    xw = None

logger = logging.getLogger(__name__)

def process_xlsm_with_xlwings(template_path: str, replacements: dict) -> str:
    """
    Procesa un archivo XLSM usando xlwings para preservar macros.
    
    Args:
        template_path: Ruta al archivo XLSM original
        replacements: Diccionario con los reemplazos a aplicar
        
    Returns:
        str: Ruta al archivo procesado (temporal)
        
    Raises:
        Exception: Si xlwings no está disponible o hay errores en el procesamiento
    """
    if xw is None:
        raise Exception("xlwings no está instalado")
    
    # Crear un archivo temporal con el mismo nombre que el original
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, os.path.basename(template_path))
    
    # Copiar el archivo original al temporal
    shutil.copy2(template_path, temp_file_path)
    
    # DEBUG: Log de reemplazos relevantes
    _log_relevant_replacements(replacements)
    
    # Usar xlwings para aplicar los reemplazos y preservar macros
    app = xw.App(visible=False)
    try:
        wb = app.books.open(temp_file_path)
        
        # Aplicar solo los reemplazos básicos en todas las hojas
        for sheet in wb.sheets:
            # DEBUG: Verificar presencia de encabezados en la hoja antes de reemplazar
            _log_sheet_headers(sheet)
            
            _apply_replacements_to_sheet(sheet, replacements)
        
        # Guardar y cerrar
        wb.save()
        wb.close()
        return temp_file_path
        
    finally:
        app.quit()

def _log_relevant_replacements(replacements: dict):
    """
    Registra en el log los reemplazos relevantes para debugging.
    """
    try:
        logger.info(f"[XLSM] Reemplazos construidos: total={len(replacements)}")
        relevant_keys = [
            'Entidad:', 'Entidad: ',
            'Auditoría:', 'Auditoría: ', 'Auditoria:', 'Auditoria: ',
            'Período:', 'Período: ', 'Periodo:', 'Periodo: ',
            '[IDENTIDAD]', '[TITULO_AUDITORIA]', '[FECHA_RANGO]',
            '[ENTIDAD_COMPLETA]', '[AUDITORIA_COMPLETA]', '[FECHA_RANGO_COMPLETA]'
        ]
        
        for key in relevant_keys:
            if key in replacements:
                logger.info(f"[XLSM] Clave presente en replacements: '{key}' -> '{replacements.get(key)}'")
    except Exception:
        pass

def _log_sheet_headers(sheet):
    """
    Registra en el log los encabezados encontrados en una hoja para debugging.
    """
    try:
        header_variants = [
            'Entidad:', 'Entidad: ',
            'Auditoría:', 'Auditoría: ', 'Auditoria:', 'Auditoria: ',
            'Período:', 'Período: ', 'Periodo:', 'Periodo: ',
        ]
        found_any = []
        for hv in header_variants:
            try:
                c = sheet.api.Cells.Find(hv)
                if c is not None:
                    found_any.append(hv)
            except Exception:
                continue
        logger.info(f"[XLSM] Hoja '{sheet.name}': encabezados encontrados (pre): {found_any}")
    except Exception:
        pass

def _apply_replacements_to_sheet(sheet, replacements: dict):
    """
    Aplica los reemplazos a una hoja específica usando xlwings.
    
    Args:
        sheet: Hoja de xlwings
        replacements: Diccionario con los reemplazos
    """
    for search_text, replace_text in replacements.items():
        try:
            # Solo buscar si hay contenido y el reemplazo existe
            if search_text and replace_text and search_text != replace_text:
                # Usar find para ubicar los textos a reemplazar
                try:
                    found_cell = sheet.api.Cells.Find(search_text)
                    if found_cell is not None:  # Verificar que no sea None
                        first_address = found_cell.Address
                        while found_cell is not None:  # Verificar en cada iteración
                            found_cell.Value = replace_text
                            found_cell = sheet.api.Cells.FindNext(found_cell)
                            # Evitar bucle infinito
                            if found_cell is None or found_cell.Address == first_address:
                                break
                except Exception as e:
                    logger.warning(f"Error al buscar texto '{search_text}': {str(e)}")
        except Exception as e:
            logger.warning(f"Error al reemplazar '{search_text}': {str(e)}")

def is_xlwings_available() -> bool:
    """
    Verifica si xlwings está disponible.
    
    Returns:
        bool: True si xlwings está disponible, False en caso contrario
    """
    return xw is not None
