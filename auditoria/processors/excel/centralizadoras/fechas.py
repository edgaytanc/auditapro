import re
from datetime import datetime
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment

def obtener_todas_fechas_semestrales(balances):
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

def filtrar_cuentas_por_seccion(balances, fecha, seccion):
    """
    Filtra las cuentas de una sección específica para una fecha dada

    Args:
        balances: Diccionario con los balances financieros
        fecha: Fecha en formato YYYY-MM-DD
        seccion: Nombre de la sección (Activo, Pasivo, Patrimonio, ESTADO DE RESULTADOS)

    Returns:
        Diccionario con las cuentas y sus valores
    """
    cuentas_filtradas = {}
    patron = re.compile(f'SEMESTRAL-{fecha}-{seccion}-(.*)')

    for clave, valor in balances.items():
        match = patron.match(clave)
        if match:
            nombre_cuenta = match.group(1)
            cuentas_filtradas[nombre_cuenta] = valor

    return cuentas_filtradas

def preparar_fechas_excel(fechas_semestrales):
    """
    Prepara las fechas para mostrar en Excel

    Args:
        fechas_semestrales: Lista con todas las fechas semestrales

    Returns:
        Tuple con (fechas_año_viejo, fecha_mas_reciente, año_mas_viejo, año_mas_reciente, fechas_excel)
    """
    # Ordenar fechas por año
    fechas_por_año = {}
    for fecha in fechas_semestrales:
        año = fecha.split('-')[0]
        if año not in fechas_por_año:
            fechas_por_año[año] = []
        fechas_por_año[año].append(fecha)

    # Ordenar años
    años_ordenados = sorted(fechas_por_año.keys())

    if not años_ordenados:
        return [], "", "", "", {}

    # Obtener el año más viejo y el más reciente
    año_mas_viejo = años_ordenados[0]
    año_mas_reciente = años_ordenados[-1]

    # Obtener las fechas del año más viejo (ordenadas)
    fechas_año_viejo = sorted(fechas_por_año[año_mas_viejo])

    # Verificar si tenemos suficientes fechas para el año más viejo
    while len(fechas_año_viejo) < 3:
        if fechas_año_viejo:
            fechas_año_viejo.append(fechas_año_viejo[-1])
        else:
            fechas_año_viejo.append("")

    # Obtener la fecha más reciente del año más reciente
    fecha_mas_reciente = sorted(fechas_por_año[año_mas_reciente])[-1]

    # Formatear fechas para Excel
    fechas_excel = {
        'D12': f"Al 01/01/{año_mas_viejo}",
        'E12': f"Al 31/07/{año_mas_viejo}",
        'F12': f"Al 31/12/{año_mas_viejo}",
        'I12': f"Al 31/12/{año_mas_reciente}"
    }

    return fechas_año_viejo, fecha_mas_reciente, año_mas_viejo, año_mas_reciente, fechas_excel

def insertar_fechas_en_celdas(sheet, fechas_excel):
    """
    Inserta las fechas en las celdas correspondientes

    Args:
        sheet: Hoja de Excel
        fechas_excel: Diccionario con las fechas a insertar
    """
    for celda, fecha in fechas_excel.items():
        sheet[celda] = fecha
        sheet[celda].alignment = Alignment(horizontal='center')
