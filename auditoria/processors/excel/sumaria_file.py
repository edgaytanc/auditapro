import logging
import re
from datetime import datetime
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

def process_sumaria_file(workbook, balances, file_name):
    """
    Procesa archivos SUMARIA insertando datos de balances financieros
    
    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros
        file_name: Nombre del archivo a procesar
    
    Returns:
        El libro de Excel procesado
    """
    # Obtener la hoja activa
    sheet = workbook.active
    
    # Obtener fechas semestrales de los balances
    fechas_semestrales = obtener_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook
    
    # Determinar la cuenta basada en el nombre del archivo
    cuenta_asociada = determinar_cuenta_por_nombre_archivo(file_name)
    if not cuenta_asociada:
        return workbook
    
    
    # Verificar si es un archivo especial que requiere todas las cuentas de una sección
    es_archivo_especial = "PATRIMONIO" in file_name.upper() or "ESTADO RESULTADOS" in file_name.upper()
    
    if es_archivo_especial:
        # Determinar la sección basada en el nombre del archivo
        seccion = "Patrimonio" if "PATRIMONIO" in file_name.upper() else "ESTADO DE RESULTADOS"
        
        # Obtener todas las cuentas de la sección
        todas_cuentas = obtener_todas_cuentas_seccion(balances, fechas_semestrales, seccion)
        if not todas_cuentas:
            return workbook
        
        # Buscar la tabla en la hoja
        tabla_info = buscar_tabla_sumaria(sheet)
        if not tabla_info:
            return workbook
        
        # Actualizar fechas en los encabezados
        actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
        
        # Insertar todas las cuentas de la sección
        insertar_multiples_cuentas(sheet, todas_cuentas, fechas_semestrales, tabla_info)
    else:
        # Verificar si la cuenta existe en los balances
        cuenta_existe, datos_cuenta = verificar_cuenta_en_balances(balances, cuenta_asociada, fechas_semestrales)
        if not cuenta_existe:
            return workbook
        
        # Buscar la tabla en la hoja (aunque ahora usamos posiciones fijas, mantenemos esta
        # función para compatibilidad y posible uso futuro)
        tabla_info = buscar_tabla_sumaria(sheet)
        if not tabla_info:
            return workbook
        
        # Actualizar fechas en los encabezados
        actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
        
        # Insertar datos de la cuenta en la tabla
        insertar_datos_cuenta(sheet, datos_cuenta, tabla_info, cuenta_asociada)
    
    return workbook

def obtener_fechas_semestrales(balances):
    """
    Obtiene todas las fechas semestrales disponibles en los balances
    
    Args:
        balances: Diccionario con los balances financieros
    
    Returns:
        Lista con todas las fechas semestrales en formato YYYY-MM-DD
    """
    patron_fecha = re.compile(r'SEMESTRAL-(\d{4}-\d{2}-\d{2})')
    fechas = set()
    
    for clave in balances:
        match = patron_fecha.search(clave)
        if match:
            fecha_completa = match.group(1)
            fechas.add(fecha_completa)
    
    # Devolver las fechas ordenadas
    return sorted(list(fechas))

def determinar_cuenta_por_nombre_archivo(file_name):
    """
    Determina la cuenta asociada basada en el nombre del archivo
    
    Args:
        file_name: Nombre del archivo
    
    Returns:
        Nombre de la cuenta asociada o None si no se puede determinar
    """
    # Eliminar extensión y números del inicio
    nombre_limpio = re.sub(r'^\d+\s*', '', file_name.replace('.xlsx', ''))
    
    # Mapeo de palabras clave a nombres de cuentas
    mapeo_cuentas = {
        'CAJA': 'Caja y Bancos',
        'BANCO': 'Caja y Bancos',
        'COBRAR': 'Cuentas por Cobrar',
        'CLIENTE': 'Cuentas por Cobrar',
        'INVENTARIO': 'Inventarios',
        'INVERSION': 'Inversiones',
        'CONSTRUCCION': 'Construcciones en Proceso',
        'PROCESO': 'Construcciones en Proceso',
        'ACTIVO FIJO': 'Propiedad, Planta y Equipo',
        'PROPIEDAD': 'Propiedad, Planta y Equipo',
        'PLANTA': 'Propiedad, Planta y Equipo',
        'EQUIPO': 'Propiedad, Planta y Equipo',
        'INTANGIBLE': 'Activos Intangibles',
        'PAGAR': 'Cuentas por Pagar',
        'PROVEEDOR': 'Cuentas por Pagar',
        'PASIVO LARGO PLAZO': 'Pasivo Largo Plazo',
        'PASIVO': 'Pasivo',
        'PRESTAMO': 'Préstamos por Pagar',
        'FINANCIAMIENTO': 'Préstamos por Pagar',
        'PATRIMONIO': 'Patrimonio',
        'CAPITAL': 'Capital',
        'RESULTADO': 'Estado de Resultados',
        'INGRESO': 'Ingresos',
        'EGRESO': 'Egresos',
        'GASTO': 'Gastos',
        'COSTO': 'Costos'
    }
    
    # Buscar palabras clave en el nombre del archivo (de más específico a menos)
    palabras_clave_ordenadas = sorted(mapeo_cuentas.keys(), key=len, reverse=True)
    for palabra_clave in palabras_clave_ordenadas:
        if palabra_clave in nombre_limpio.upper():
            cuenta = mapeo_cuentas[palabra_clave]
            return cuenta
    
    # Si no se encuentra una coincidencia específica, extraer el nombre después de "SUMARIA"
    match = re.search(r'SUMARIA\s+(.*?)(?:\s+|$)', nombre_limpio.upper())
    if match:
        cuenta = match.group(1).title()
        return cuenta
    return None

def verificar_cuenta_en_balances(balances, cuenta_asociada, fechas_semestrales):
    """
    Verifica si la cuenta existe en los balances semestrales y obtiene sus datos
    
    Args:
        balances: Diccionario con los balances financieros
        cuenta_asociada: Nombre de la cuenta a buscar
        fechas_semestrales: Lista de fechas semestrales disponibles
    
    Returns:
        Tupla (bool, dict): Indica si la cuenta existe y un diccionario con los valores por fecha
    """
    datos_cuenta = {}
    cuenta_existe = False
    
    # Normalizar el nombre de la cuenta para comparaciones
    cuenta_normalizada = cuenta_asociada.lower().strip()
    
    # Buscar la cuenta en todas las secciones y fechas semestrales
    for seccion in ['Activo', 'Pasivo', 'Patrimonio', 'ESTADO DE RESULTADOS']:
        for fecha in fechas_semestrales:
            # Buscar coincidencias exactas primero
            clave_exacta = f'SEMESTRAL-{fecha}-{seccion}-{cuenta_asociada}'
            if clave_exacta in balances:
                datos_cuenta[fecha] = balances[clave_exacta]
                cuenta_existe = True
                continue
            
            # Si no hay coincidencia exacta, buscar coincidencias parciales
            if fecha not in datos_cuenta:
                for clave, valor in balances.items():
                    if clave.startswith(f'SEMESTRAL-{fecha}-{seccion}-'):
                        # Extraer el nombre de la cuenta de la clave
                        partes = clave.split('-')
                        if len(partes) >= 4:
                            nombre_cuenta = '-'.join(partes[3:])
                            nombre_cuenta_normalizado = nombre_cuenta.lower().strip()
                            
                            # Verificar si hay coincidencia parcial en ambas direcciones
                            if (cuenta_normalizada in nombre_cuenta_normalizado or 
                                nombre_cuenta_normalizado in cuenta_normalizada):
                                datos_cuenta[fecha] = valor
                                cuenta_existe = True
                                break
    return cuenta_existe, datos_cuenta

def buscar_tabla_sumaria(sheet):
    """
    Busca la tabla SUMARIA en la hoja y obtiene información sobre su estructura
    
    Args:
        sheet: Hoja de Excel a procesar
    
    Returns:
        Diccionario con información de la tabla o None si no se encuentra
    """
    # Buscar la fila que contiene "CÉDULA SUMARIA" o similar
    fila_titulo = None
    for row_idx in range(1, 30):
        for col_idx in range(1, 15):
            cell_value = sheet.cell(row=row_idx, column=col_idx).value
            if isinstance(cell_value, str) and ("SUMARIA" in cell_value.upper() or "CEDULA" in cell_value.upper()):
                fila_titulo = row_idx
                break
        if fila_titulo:
            break
    
    if not fila_titulo:
        return None
    
    # Buscar la fila de encabezados (contiene "SALDOS S/ BALANCE")
    fila_encabezados = None
    for row_idx in range(fila_titulo, fila_titulo + 15):
        for col_idx in range(1, 15):
            cell_value = sheet.cell(row=row_idx, column=col_idx).value
            if isinstance(cell_value, str) and "SALDOS S/ BALANCE" in cell_value.upper():
                fila_encabezados = row_idx
                break
        if fila_encabezados:
            break
    
    if not fila_encabezados:
        return None
    
    # Identificar columnas de fechas
    columnas_fechas = []
    for col_idx in range(1, 15):
        cell_value = sheet.cell(row=fila_encabezados, column=col_idx).value
        if isinstance(cell_value, str) and "SALDOS S/ BALANCE" in cell_value.upper():
            columnas_fechas.append(col_idx)
    
    # Identificar columna de cuenta
    columna_cuenta = None
    for col_idx in range(1, 15):
        cell_value = sheet.cell(row=fila_encabezados + 1, column=col_idx).value
        if isinstance(cell_value, str) and ("CUENTA" in cell_value.upper() or "DESCRIPCIÓN" in cell_value.upper()):
            columna_cuenta = col_idx
            break
    
    # Identificar fila donde empiezan los datos
    fila_inicio_datos = fila_encabezados + 2
    
    return {
        'fila_titulo': fila_titulo,
        'fila_encabezados': fila_encabezados,
        'fila_inicio_datos': fila_inicio_datos,
        'columnas_fechas': columnas_fechas,
        'columna_cuenta': columna_cuenta
    }

def actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info):
    """
    Actualiza las fechas en los encabezados de la tabla
    
    Args:
        sheet: Hoja de Excel a procesar
        fechas_semestrales: Lista de fechas semestrales disponibles
        tabla_info: Información de la tabla
    """
    # Ordenar fechas por año y mes
    fechas_ordenadas = sorted(fechas_semestrales)
    
    # Formatear fechas para mostrar en Excel (DD/MM/YYYY)
    fechas_formateadas = []
    for fecha in fechas_ordenadas:
        partes = fecha.split('-')
        if len(partes) == 3:
            fechas_formateadas.append(f"{partes[2]}/{partes[1]}/{partes[0]}")
    
    # Celdas específicas para las fechas (solo en la fila 12)
    celdas_fechas = ['E12', 'F12', 'G12', 'J12']
    
    # Insertar fechas en las celdas específicas
    for i, celda in enumerate(celdas_fechas):
        if i < len(fechas_formateadas):
            # Verificar si la celda ya tiene un formato específico (como "AL DD/MM/AAAA")
            valor_actual = sheet[celda].value
            if isinstance(valor_actual, str) and "AL " in valor_actual.upper():
                sheet[celda].value = f"AL {fechas_formateadas[i]}"
            else:
                sheet[celda].value = fechas_formateadas[i]
            
            # Centrar la celda
            sheet[celda].alignment = Alignment(horizontal='center')

def insertar_datos_cuenta(sheet, datos_cuenta, tabla_info, nombre_cuenta="TOTAL"):
    """
    Inserta los datos de la cuenta en la tabla
    
    Args:
        sheet: Hoja de Excel a procesar
        datos_cuenta: Diccionario con los valores de la cuenta por fecha
        tabla_info: Información de la tabla
        nombre_cuenta: Nombre de la cuenta a insertar
    """
    # Ordenar fechas
    fechas_ordenadas = sorted(datos_cuenta.keys())
    
    # Insertar el nombre de la cuenta en la celda B13
    sheet['B13'].value = nombre_cuenta
    
    # Celdas específicas para los valores (solo en la fila 13)
    celdas_valores = ['E13', 'F13', 'G13', 'J13']
    
    # Insertar valores en las celdas específicas
    for i, celda in enumerate(celdas_valores):
        if i < len(fechas_ordenadas):
            fecha = fechas_ordenadas[i]
            if fecha in datos_cuenta:
                sheet[celda].value = datos_cuenta[fecha]

def obtener_todas_cuentas_seccion(balances, fechas_semestrales, seccion):
    """
    Obtiene todas las cuentas de una sección específica
    
    Args:
        balances: Diccionario con los balances financieros
        fechas_semestrales: Lista de fechas semestrales disponibles
        seccion: Nombre de la sección (Patrimonio, ESTADO DE RESULTADOS)
    
    Returns:
        Diccionario con las cuentas y sus valores por fecha
    """
    # Diccionario para almacenar todas las cuentas encontradas
    todas_cuentas = {}
    
    # Patrón para encontrar cuentas de la sección
    patron = re.compile(f'SEMESTRAL-(.*?)-{seccion}-(.*)')
    
    # Buscar todas las cuentas de la sección en los balances
    for clave, valor in balances.items():
        match = patron.match(clave)
        if match:
            fecha, nombre_cuenta = match.groups()
            
            # Solo procesar las fechas que están en fechas_semestrales
            if fecha in fechas_semestrales:
                # Inicializar el diccionario para esta cuenta si no existe
                if nombre_cuenta not in todas_cuentas:
                    todas_cuentas[nombre_cuenta] = {}
                
                # Guardar el valor para esta fecha
                todas_cuentas[nombre_cuenta][fecha] = valor
    
    return todas_cuentas

def insertar_multiples_cuentas(sheet, todas_cuentas, fechas_semestrales, tabla_info):
    """
    Inserta múltiples cuentas en la tabla, insertando filas adicionales si es necesario
    
    Args:
        sheet: Hoja de Excel a procesar
        todas_cuentas: Diccionario con las cuentas y sus valores por fecha
        fechas_semestrales: Lista de fechas semestrales disponibles
        tabla_info: Información de la tabla
    """
    # Ordenar las fechas
    fechas_ordenadas = sorted(fechas_semestrales)
    
    # Ordenar las cuentas alfabéticamente
    cuentas_ordenadas = sorted(todas_cuentas.keys())
    
    # Determinar cuántas filas necesitamos insertar
    filas_necesarias = len(cuentas_ordenadas)
    filas_disponibles = 1  # Solo la fila 13 está disponible inicialmente
    filas_a_insertar = max(0, filas_necesarias - filas_disponibles)
    
    # Verificar si las celdas B13 y C13 están combinadas
    celdas_combinadas_originales = []
    for merged_cell_range in sheet.merged_cells.ranges:
        if 13 in range(merged_cell_range.min_row, merged_cell_range.max_row + 1):
            celdas_combinadas_originales.append({
                'min_row': merged_cell_range.min_row,
                'max_row': merged_cell_range.max_row,
                'min_col': merged_cell_range.min_col,
                'max_col': merged_cell_range.max_col
            })
    # Si necesitamos insertar filas adicionales
    if filas_a_insertar > 0:
        # Guardar el estilo de la fila 13 para aplicarlo a las nuevas filas
        estilos_fila_13 = {}
        formulas_fila_13 = {}
        
        # Capturar estilos y fórmulas de la fila 13
        for col in range(1, sheet.max_column + 1):
            celda_origen = sheet.cell(row=13, column=col)
            estilos_fila_13[col] = {
                'font': celda_origen.font.copy() if celda_origen.font else None,
                'border': celda_origen.border.copy() if celda_origen.border else None,
                'fill': celda_origen.fill.copy() if celda_origen.fill else None,
                'number_format': celda_origen.number_format,
                'alignment': celda_origen.alignment.copy() if celda_origen.alignment else None,
                'protection': celda_origen.protection.copy() if celda_origen.protection else None
            }
            
            # Capturar fórmulas
            if celda_origen.data_type == 'f':
                formulas_fila_13[col] = celda_origen.value
        
        # Insertar filas después de la fila 13
        sheet.insert_rows(14, filas_a_insertar)
        
        # Aplicar estilos y fórmulas a las nuevas filas
        for i in range(filas_a_insertar):
            fila_destino = 14 + i
            for col, estilos in estilos_fila_13.items():
                celda_destino = sheet.cell(row=fila_destino, column=col)
                
                # Aplicar estilos
                if estilos['font']: celda_destino.font = estilos['font']
                if estilos['border']: celda_destino.border = estilos['border']
                if estilos['fill']: celda_destino.fill = estilos['fill']
                celda_destino.number_format = estilos['number_format']
                if estilos['alignment']: celda_destino.alignment = estilos['alignment']
                if estilos['protection']: celda_destino.protection = estilos['protection']
                
                # Aplicar fórmulas si existen, ajustando las referencias de fila
                if col in formulas_fila_13:
                    formula = formulas_fila_13[col]
                    if isinstance(formula, str) and formula.startswith('='):
                        formula_ajustada = ajustar_formula_para_nueva_fila(formula, 13, fila_destino)
                        celda_destino.value = formula_ajustada
            
            # Aplicar combinación de celdas si es necesario
            for celda_combinada in celdas_combinadas_originales:
                # Crear una nueva combinación de celdas en la misma posición relativa
                min_col = celda_combinada['min_col']
                max_col = celda_combinada['max_col']
                
                # Solo combinar si hay más de una celda en el rango
                if max_col > min_col:
                    rango_combinacion = f"{get_column_letter(min_col)}{fila_destino}:{get_column_letter(max_col)}{fila_destino}"
                    sheet.merge_cells(rango_combinacion)
    
    # Insertar las cuentas en las filas
    for i, nombre_cuenta in enumerate(cuentas_ordenadas):
        if i >= filas_necesarias:
            break
        
        # Determinar la fila donde insertar esta cuenta
        fila_destino = 13 + i
        
        # Insertar el nombre de la cuenta en la columna B
        # Si B y C están combinadas, el valor va en la celda B
        sheet[f'B{fila_destino}'].value = nombre_cuenta
        
        # Insertar valores en las columnas E, F, G, J
        celdas_valores = ['E', 'F', 'G', 'J']
        
        for j, col in enumerate(celdas_valores):
            if j < len(fechas_ordenadas):
                fecha = fechas_ordenadas[j]
                if fecha in todas_cuentas[nombre_cuenta]:
                    sheet[f'{col}{fila_destino}'].value = todas_cuentas[nombre_cuenta][fecha]
    
def ajustar_formula_para_nueva_fila(formula, fila_origen, fila_destino):
    """
    Ajusta la fórmula para la nueva fila, cambiando las referencias de fila
    
    Args:
        formula: Fórmula original
        fila_origen: Fila original de la fórmula
        fila_destino: Fila destino de la fórmula
    
    Returns:
        Fórmula ajustada para la nueva fila
    """
    # Reemplazar las referencias de fila
    formula_ajustada = formula.replace(f"${fila_origen}", f"${fila_destino}")
    
    return formula_ajustada