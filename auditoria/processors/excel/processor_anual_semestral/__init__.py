from .data_extraction import extraer_y_clasificar_datos
from .sheet_processing import procesar_hoja_anual, procesar_hoja_semestral

def process_anual_semestral_sheets(workbook, balances):
    """Procesa las hojas ANUAL y SEMESTRAL del Excel insertando las fechas y cuentas."""
    # 1. Extraer y clasificar todos los datos necesarios
    datos = extraer_y_clasificar_datos(balances)

    # 2. Procesar cada hoja del libro de trabajo
    for sheet in workbook.worksheets:
        sheet_title = sheet.title.upper()

        try:
            if sheet_title in ['ACTUAL', 'ANUAL'] and datos['fechas_anual']:
                procesar_hoja_anual(sheet, datos['cuentas_anual'], datos['fechas_anual'], balances)
            
            elif sheet_title == 'SEMESTRAL' and datos['fechas_semestral']:
                procesar_hoja_semestral(sheet, datos['cuentas_semestral'], datos['fechas_semestral'], balances)
        except Exception as e:
            pass
            
    return workbook
