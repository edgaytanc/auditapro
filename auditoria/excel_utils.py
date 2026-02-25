import logging
import os
import tempfile
import shutil
from openpyxl import load_workbook
try:
    import xlwings as xw
except ImportError:
    xw = None
from .processors.excel.sheet_processor import process_excel_sheets
from .utils.replacements_utils import (
    get_replacements_config,
    get_tables_config,
    build_replacements_dict,
)
from .utils.data_db import get_all_financial_data

logger = logging.getLogger(__name__)

def modify_document_excel(template_path, audit):
    
    wb = load_workbook(template_path)

    fecha_inicio = audit.fechaInit.strftime('%d de %B de %Y') if audit.fechaInit else '01 de Enero de 2024'
    fecha_fin = audit.fechaEnd.strftime('%d de %B de %Y') if audit.fechaEnd else '31 de Diciembre de 2024'

    meses = {
        'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
        'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
        'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
    }

    for eng, esp in meses.items():
        fecha_inicio = fecha_inicio.replace(eng, esp)
        fecha_fin = fecha_fin.replace(eng, esp)

    fecha_inicio_parts = fecha_inicio.split(' ')
    fecha_fin_parts = fecha_fin.split(' ')

    if len(fecha_inicio_parts) >= 4:
        fecha_inicio = f"{fecha_inicio_parts[0].zfill(2)} de {fecha_inicio_parts[2].capitalize()} de {fecha_inicio_parts[4]}"
    if len(fecha_fin_parts) >= 4:
        fecha_fin = f"{fecha_fin_parts[0].zfill(2)} de {fecha_fin_parts[2].capitalize()} de {fecha_fin_parts[4]}"

    # Obtener datos financieros
    financial_data = get_all_financial_data(audit.id)
    
    data_bd = financial_data['organized']
    
    replacements_config = get_replacements_config()
    tables_config = get_tables_config()
    
    # Obtener los reemplazos básicos
    replacements = build_replacements_dict(
        config=replacements_config,
        audit=audit,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    print(data_bd)
    # Procesar el documento Excel
    process_excel_sheets(wb, tables_config, replacements, data_bd, template_path)
    
    return wb

def modify_document_excel_with_macros(template_path, audit):
    """
    Procesa archivos Excel con macros (.xlsm) manteniendo las macros intactas.
    Aplica solo los reemplazos básicos de texto usando xlwings.
    
    Args:
        template_path: Ruta al archivo XLSM original
        audit: Objeto Audit con los datos para reemplazar
        
    Returns:
        string: Ruta al archivo procesado (puede ser el mismo o un temporal)
    """
    if xw is None:
        logger.warning("xlwings no está instalado. Se devolverá el archivo original sin procesar.")
        return template_path
    
    # Crear un archivo temporal con el mismo nombre que el original
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, os.path.basename(template_path))
    
    # Copiar el archivo original al temporal
    shutil.copy2(template_path, temp_file_path)
    
    try:
        # Preparar los datos para reemplazos
        fecha_inicio = audit.fechaInit.strftime('%d de %B de %Y') if audit.fechaInit else '01 de Enero de 2024'
        fecha_fin = audit.fechaEnd.strftime('%d de %B de %Y') if audit.fechaEnd else '31 de Diciembre de 2024'
        
        # Traducir nombres de meses a español
        meses = {
            'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
            'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
            'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
        }
        
        for eng, esp in meses.items():
            fecha_inicio = fecha_inicio.replace(eng, esp)
            fecha_fin = fecha_fin.replace(eng, esp)
        
        # Formatear fechas
        fecha_inicio_parts = fecha_inicio.split(' ')
        fecha_fin_parts = fecha_fin.split(' ')
        
        if len(fecha_inicio_parts) >= 4:
            fecha_inicio = f"{fecha_inicio_parts[0].zfill(2)} de {fecha_inicio_parts[2].capitalize()} de {fecha_inicio_parts[4]}"
        if len(fecha_fin_parts) >= 4:
            fecha_fin = f"{fecha_fin_parts[0].zfill(2)} de {fecha_fin_parts[2].capitalize()} de {fecha_fin_parts[4]}"
        
        # Obtener la configuración de reemplazos
        replacements_config = get_replacements_config()
        
        # Construir el diccionario de reemplazos usando la misma función que modify_document_excel
        replacements = build_replacements_dict(
            config=replacements_config,
            audit=audit,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        )
        
        # Usar xlwings para aplicar los reemplazos y preservar macros
        app = xw.App(visible=False)
        try:
            wb = app.books.open(temp_file_path)
            
            # Aplicar solo los reemplazos básicos en todas las hojas
            for sheet in wb.sheets:
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
            
            # Guardar y cerrar
            wb.save()
            wb.close()
            return temp_file_path
            
        finally:
            app.quit()
            
    except Exception as e:
        logger.error(f"Error al procesar archivo XLSM: {str(e)}")
        return template_path