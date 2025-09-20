import logging
from .data_extraction import (
    obtener_fecha_ultimo_dia_año_reciente,
    extraer_cuentas_balance_ultimo_dia,
    extraer_cuentas_saldos_iniciales
)
from .sheet_processing import (
    actualizar_fechas_encabezados,
    buscar_fila_encabezado,
    insertar_datos_en_hoja
)

logger = logging.getLogger(__name__)

def process_initial_balance_tests(workbook, balances, saldos_iniciales):
    """Procesa el archivo de pruebas de saldos iniciales"""
    # Extraer fechas y cuentas
    fecha_ultimo_dia, año_mas_reciente = obtener_fecha_ultimo_dia_año_reciente(balances)
    if not fecha_ultimo_dia:
        return workbook
    
    cuentas_balance = extraer_cuentas_balance_ultimo_dia(balances, fecha_ultimo_dia)
    cuentas_saldos_iniciales, fecha_saldos_iniciales = extraer_cuentas_saldos_iniciales(saldos_iniciales)
    
    # Procesar cada hoja del libro
    for sheet in workbook.worksheets:
        actualizar_fechas_encabezados(sheet, fecha_ultimo_dia, fecha_saldos_iniciales)
        
        if fila_encabezado := buscar_fila_encabezado(sheet):
            insertar_datos_en_hoja(sheet, fila_encabezado, cuentas_balance, 
                                  cuentas_saldos_iniciales, fecha_ultimo_dia)
    
    return workbook
