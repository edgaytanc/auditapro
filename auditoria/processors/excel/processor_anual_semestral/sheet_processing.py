from .row_inserter import insertar_cuentas_en_hoja
from .utils import formatear_fecha

def procesar_hoja_anual(sheet, cuentas_anual, fechas_anual, balances):
    """Procesa la hoja ANUAL/ACTUAL."""
    insertar_cuentas_en_hoja(sheet, cuentas_anual, 'ANUAL', fechas_anual, balances)

def procesar_hoja_semestral(sheet, cuentas_semestral, fechas_semestral, balances):
    """Procesa la hoja SEMESTRAL."""
    fechas_formateadas = [formatear_fecha(f) for f in fechas_semestral]
    # Insertar fechas en la fila 14, máximo 4
    for i, fecha in enumerate(fechas_formateadas[:4]):
        sheet.cell(row=14, column=i + 3).value = fecha
    
    insertar_cuentas_en_hoja(sheet, cuentas_semestral, 'SEMESTRAL', fechas_semestral, balances)
