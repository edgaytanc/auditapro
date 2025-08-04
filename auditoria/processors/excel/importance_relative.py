from openpyxl.utils import get_column_letter, column_index_from_string
from openpyxl.worksheet.table import Table, TableStyleInfo

def process_importance_relative(workbook, balances):
    """
    Procesa específicamente el archivo de Importancia Relativa, insertando datos
    de balances en las tablas correspondientes.
    
    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los datos de balances financieros
    
    Returns:
        workbook: El libro de Excel procesado
    """
    # Identificar el año más reciente en los balances
    anios = set()
    for key in balances.keys():
        if key.startswith('ANUAL-'):
            parts = key.split('-')
            if len(parts) > 1:
                anios.add(parts[1])
    
    if not anios:
        return workbook
        
    anio_actual = max(anios)
    
    # Procesar cada hoja específica
    for sheet_name in workbook.sheetnames:
        if "IR INGRESOS TOTALES" in sheet_name.upper():
            process_ir_ingresos_totales(sheet_name, workbook, balances, anio_actual)
        elif "IR ACTIVOS TOTALES" in sheet_name.upper():
            process_ir_activos_totales(sheet_name, workbook, balances, anio_actual)
        elif "IR UTILIDAD" in sheet_name.upper():
            process_ir_utilidad(sheet_name, workbook, balances, anio_actual)
    
    return workbook

def process_ir_ingresos_totales(sheet_name, workbook, balances, anio_actual):
    """
    Procesa la hoja de IR INGRESOS TOTALES, buscando la cuenta 'Ingresos totales'
    en los balances del año actual y llenando la tabla correspondiente.
    
    Args:
        sheet_name: Nombre de la hoja a procesar
        workbook: Libro de Excel
        balances: Diccionario con los datos de balances
        anio_actual: Año más reciente identificado
    """
    
    # Buscar la cuenta 'Ingresos totales' para el año actual
    ingresos_key = f"ANUAL-{anio_actual}-ESTADO DE RESULTADOS-Ingresos totales"
    ingresos_totales = None
    cuenta_encontrada = False
    
    # Si la clave exacta no está, buscar algo similar
    if ingresos_key in balances:
        ingresos_totales = balances[ingresos_key]
        cuenta_encontrada = True
    else:
        # Buscar cualquier clave que contenga los elementos relevantes
        for key, value in balances.items():
            if (f"ANUAL-{anio_actual}" in key and 
                "ESTADO DE RESULTADOS" in key and 
                "Ingresos totales" in key):
                ingresos_totales = value
                ingresos_key = key
                cuenta_encontrada = True
                break
    
    # Acceder a la hoja
    sheet = workbook[sheet_name]
    
    # Colocar valores en las celdas B26 y C26
    if cuenta_encontrada:
        sheet['B26'].value = "INGRESOS TOTALES"
        sheet['C26'].value = ingresos_totales
    else:
        sheet['B26'].value = "NO EXISTE"
        sheet['C26'].value = 0

def process_ir_activos_totales(sheet_name, workbook, balances, anio_actual):
    """
    Procesa la hoja de IR ACTIVOS TOTALES, calculando la suma de todos los activos
    del balance anual (o semestral si no hay anual) para el año actual.
    
    Args:
        sheet_name: Nombre de la hoja a procesar
        workbook: Libro de Excel
        balances: Diccionario con los datos de balances
        anio_actual: Año más reciente identificado
    """
    # Variables para almacenar los totales de activos
    activos_totales = 0
    
    # Obtener la fecha completa más reciente para ANUAL y SEMESTRAL
    anual_fecha = None
    semestral_fecha = None
    
    for key in balances.keys():
        if f"ANUAL-{anio_actual}" in key:
            parts = key.split('-')
            if len(parts) >= 3:  # Asegurarse de que hay suficientes partes para formar una fecha
                fecha = f"{parts[1]}-{parts[2]}"
                if anual_fecha is None or fecha > anual_fecha:
                    anual_fecha = fecha
        elif f"SEMESTRAL-{anio_actual}" in key:
            parts = key.split('-')
            if len(parts) >= 3:  # Asegurarse de que hay suficientes partes para formar una fecha
                fecha = f"{parts[1]}-{parts[2]}"
                if semestral_fecha is None or fecha > semestral_fecha:
                    semestral_fecha = fecha
    
    # Determinar qué tipo de balance usar (prioridad a ANUAL)
    tipo_balance = "ANUAL" if anual_fecha else "SEMESTRAL"
    fecha_balance = anual_fecha if anual_fecha else semestral_fecha
    
    # Calcular la suma de todos los activos del balance seleccionado
    cuentas_procesadas = []
    for key, value in balances.items():
        # Solo considerar cuentas del tipo de balance elegido y del año actual
        if f"{tipo_balance}-{fecha_balance}" in key and "Activo-" in key:
            activos_totales += value
            cuentas_procesadas.append(f"{key}: {value}")
    
    # Acceder a la hoja
    sheet = workbook[sheet_name]
    
    # Colocar valores en las celdas B26 y C26
    sheet['B26'].value = "ACTIVOS TOTALES"
    sheet['C26'].value = activos_totales

def process_ir_utilidad(sheet_name, workbook, balances, anio_actual):
    """
    Procesa la hoja de IR UTILIDAD, buscando la utilidad antes de impuesto
    en los balances del año actual y llenando la tabla correspondiente.
    
    Args:
        sheet_name: Nombre de la hoja a procesar
        workbook: Libro de Excel
        balances: Diccionario con los datos de balances
        anio_actual: Año más reciente identificado
    """
    # Buscar la cuenta 'Utilidad antes de impuesto' para el año actual
    utilidad_key = f"ANUAL-{anio_actual}-ESTADO DE RESULTADOS-Utilidad antes de impuesto"
    utilidad = None
    cuenta_encontrada = False
    
    # Si la clave exacta no está, buscar algo similar
    if utilidad_key in balances:
        utilidad = balances[utilidad_key]
        cuenta_encontrada = True
    else:
        # Buscar cualquier clave que contenga los elementos relevantes
        for key, value in balances.items():
            if (f"ANUAL-{anio_actual}" in key and 
                "ESTADO DE RESULTADOS" in key and 
                "Utilidad antes de impuesto" in key):
                utilidad = value
                utilidad_key = key
                cuenta_encontrada = True
                break
    
    # Acceder a la hoja
    sheet = workbook[sheet_name]
    
    # Colocar valores en las celdas B26 y C26
    if cuenta_encontrada:
        sheet['B26'].value = "UTILIDAD ANTES DE IMPUESTOS"
        sheet['C26'].value = utilidad
    else:
        sheet['B26'].value = "NO EXISTE"
        sheet['C26'].value = 0
