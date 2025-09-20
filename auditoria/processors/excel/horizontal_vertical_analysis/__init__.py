from .data_extraction import extraer_cuentas_por_seccion
from .sheet_processing import procesar_hoja_balance

def process_horizontal_vertical_analysis(workbook, balances):
    """
    Procesa el archivo de análisis horizontal y vertical

    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros

    Returns:
        El libro de Excel procesado
    """
    balances_anuales = {k: v for k, v in balances.items() if k.startswith('ANUAL-')}
    if not balances_anuales:
        return workbook

    años = sorted(set(p.split('-')[1] for p in balances_anuales.keys() if len(p.split('-')) > 1 and p.split('-')[1].isdigit()), reverse=True)
    if len(años) < 2:
        return workbook

    cuentas_por_seccion = extraer_cuentas_por_seccion(balances_anuales, años)

    for sheet in workbook.worksheets:
        if "BALANCE" in sheet.title.upper() or "BG" in sheet.title.upper():
            procesar_hoja_balance(sheet, cuentas_por_seccion, años)
            
    return workbook
