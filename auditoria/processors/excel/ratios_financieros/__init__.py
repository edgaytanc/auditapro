import logging
from .data_extraction import extraer_fechas_anuales, clasificar_cuentas_por_seccion_y_tipo
from .sheet_processing import procesar_hoja_comparativo, procesar_hoja_analisis_vertical

logger = logging.getLogger(__name__)

def process_ratios_financieros(workbook, balances):
    """
    Procesa las hojas de ratios financieros insertando las cuentas clasificadas por tipo y año.
    """
    fechas_anual = extraer_fechas_anuales(balances)
    if len(fechas_anual) < 2:
        logger.warning("No hay suficientes fechas anuales para procesar los ratios financieros.")
        return workbook

    año_actual, año_anterior = fechas_anual[-1], fechas_anual[-2]

    cuentas_clasificadas = clasificar_cuentas_por_seccion_y_tipo(balances, año_actual, año_anterior)

    for sheet in workbook.worksheets:
        sheet_title = sheet.title.upper()
        if "ESTADOS FINANCIEROS COMPARATIVO" in sheet_title:
            procesar_hoja_comparativo(sheet, cuentas_clasificadas, año_actual, año_anterior)
        elif "ANÁLISIS VERTICAL" in sheet_title or "ANALISIS VERTICAL" in sheet_title:
            procesar_hoja_analisis_vertical(sheet, cuentas_clasificadas, año_actual, año_anterior)
            
    return workbook
