import logging
import os
import tempfile
import shutil
import zipfile
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

def _replace_in_xlsm_shared_strings(src_path: str, dst_path: str, replacements: dict):
    """Copia un .xlsm y reemplaza placeholders en:
    - xl/sharedStrings.xml
    - xl/worksheets/*.xml (inlineStr y headerFooter)
    - xl/drawings/*.xml (textos en shapes)
    Devuelve una copia con reemplazos sin tocar macros.
    """
    total_hits = 0
    files_touched = []
    with zipfile.ZipFile(src_path, 'r') as zin, zipfile.ZipFile(dst_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            needs_text_replace = (
                item.filename == 'xl/sharedStrings.xml' or
                (item.filename.startswith('xl/worksheets/') and item.filename.endswith('.xml')) or
                (item.filename.startswith('xl/drawings/') and item.filename.endswith('.xml'))
            )
            if needs_text_replace:
                try:
                    text = data.decode('utf-8')
                except UnicodeDecodeError:
                    text = data.decode('utf-8', errors='ignore')
                file_hits = 0
                for k, v in replacements.items():
                    if not isinstance(v, str):
                        v = str(v)
                    if not k:
                        continue
                    occurrences = text.count(k)
                    if occurrences:
                        text = text.replace(k, v)
                        file_hits += occurrences
                if file_hits:
                    files_touched.append((item.filename, file_hits))
                    total_hits += file_hits
                data = text.encode('utf-8')
            zout.writestr(item, data)
    logger.debug(f"XLSM fallback: total reemplazos aplicados: {total_hits}")
    for fname, hits in files_touched:
        logger.debug(f"XLSM fallback: {fname} -> {hits} reemplazos")

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
        logger.warning("xlwings no está instalado. Fallback: reemplazo en sharedStrings + worksheets + drawings (conserva macros/shapes).")
        try:
            # Preparar fechas como en la ruta principal
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
            
            fi_parts = fecha_inicio.split(' ')
            ff_parts = fecha_fin.split(' ')
            if len(fi_parts) >= 4:
                fecha_inicio = f"{fi_parts[0].zfill(2)} de {fi_parts[2].capitalize()} de {fi_parts[4]}"
            if len(ff_parts) >= 4:
                fecha_fin = f"{ff_parts[0].zfill(2)} de {ff_parts[2].capitalize()} de {ff_parts[4]}"
            
            # Construir reemplazos
            replacements_config = get_replacements_config()
            replacements_all = build_replacements_dict(
                config=replacements_config,
                audit=audit,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )
            
            # Ampliar llaves permitidas: placeholders entre corchetes o etiquetas comunes completas
            def _allow(k: str) -> bool:
                if not isinstance(k, str):
                    return False
                if k.startswith('[') and k.endswith(']'):
                    return True
                prefixes = (
                    'Entidad', 'Auditoría', 'Auditoria', 'Período', 'Periodo'
                )
                return any(k.startswith(p) for p in prefixes)
            filtered_repl = {k: v for k, v in replacements_all.items() if _allow(k)}
            
            # Forzar reemplazo de etiquetas "Período:"/"Periodo:" sin placeholder
            period_value = None
            for key in ('[FECHA_RANGO_COMPLETA]', '[FECHA_RANGO]'):
                if key in replacements_all and isinstance(replacements_all[key], (str, int, float)):
                    period_value = str(replacements_all[key])
                    break
            if period_value:
                # Variantes comunes con y sin espacio adicional
                for label in ('Período:', 'Periodo:', 'Período :', 'Periodo :'):
                    filtered_repl[label] = f"{label.split(':')[0]}: {period_value}"
                logger.debug(f"XLSM fallback: valor de período aplicado: {period_value}")
                
                # Reemplazo del literal fijo del template
                default_period_literals = [
                    'Del 01 de Enero al 31 de Diciembre de 2024',
                    'DEL 01 DE ENERO AL 31 DE DICIEMBRE DE 2024',
                    'Del 01 de enero al 31 de diciembre de 2024',
                ]
                period_only = period_value.replace('Período:', '').replace('Periodo:', '').strip()
                for lit in default_period_literals:
                    filtered_repl[lit] = period_only
            
            # Crear archivo temporal destino (mismo nombre)
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, os.path.basename(template_path))
            
            _replace_in_xlsm_shared_strings(template_path, temp_file_path, filtered_repl)
            return temp_file_path
        except Exception as e:
            logger.error(f"Fallback XLSM (package replace) falló: {str(e)}")
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
        
        # DEBUG: Log de reemplazos relevantes
        try:
            logger.info(f"[XLSM] Reemplazos construidos: total={len(replacements)}")
            for key in [
                'Entidad:', 'Entidad: ',
                'Auditoría:', 'Auditoría: ', 'Auditoria:', 'Auditoria: ',
                'Período:', 'Período: ', 'Periodo:', 'Periodo: ',
                '[IDENTIDAD]', '[TITULO_AUDITORIA]', '[FECHA_RANGO]',
                '[ENTIDAD_COMPLETA]', '[AUDITORIA_COMPLETA]', '[FECHA_RANGO_COMPLETA]'
            ]:
                if key in replacements:
                    logger.info(f"[XLSM] Clave presente en replacements: '{key}' -> '{replacements.get(key)}'")
        except Exception:
            pass
        
        # Usar xlwings para aplicar los reemplazos y preservar macros
        app = xw.App(visible=False)
        try:
            wb = app.books.open(temp_file_path)
            
            # Aplicar solo los reemplazos básicos en todas las hojas
            for sheet in wb.sheets:
                # DEBUG: Verificar presencia de encabezados en la hoja antes de reemplazar
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