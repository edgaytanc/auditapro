"""
Manejador de xlwings para procesamiento de archivos Excel con macros.
Contiene funciones para aplicar reemplazos usando xlwings preservando macros.
"""

import tempfile
import os
import shutil

try:
    import xlwings as xw
except ImportError:
    xw = None

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
    
    # Usar xlwings para aplicar los reemplazos y preservar macros
    app = xw.App(visible=False)
    try:
        wb = app.books.open(temp_file_path)
        
        # Aplicar solo los reemplazos básicos en todas las hojas
        for sheet in wb.sheets:
            _apply_replacements_to_sheet(sheet, replacements)
        
        # Guardar y cerrar
        wb.save()
        wb.close()
        return temp_file_path
        
    finally:
        app.quit()

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
                except Exception:
                    pass
        except Exception:
            pass

def is_xlwings_available() -> bool:
    """
    Verifica si xlwings está disponible.
    
    Returns:
        bool: True si xlwings está disponible, False en caso contrario
    """
    return xw is not None
