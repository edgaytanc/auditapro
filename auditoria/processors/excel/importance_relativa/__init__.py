from .ingresos_totales import process_ir_ingresos_totales
from .activos_totales import process_ir_activos_totales
from .utilidad import process_ir_utilidad


def process_importance_relative(workbook, balances):
    """
    Procesa específicamente el archivo de Importancia Relativa, insertando datos
    de balances en las tablas correspondientes.
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
        name_upper = sheet_name.upper()
        if "IR INGRESOS TOTALES" in name_upper:
            process_ir_ingresos_totales(sheet_name, workbook, balances, anio_actual)
        elif "IR ACTIVOS TOTALES" in name_upper:
            process_ir_activos_totales(sheet_name, workbook, balances, anio_actual)
        elif "IR UTILIDAD" in name_upper:
            process_ir_utilidad(sheet_name, workbook, balances, anio_actual)

    return workbook

__all__ = [
    'process_importance_relative',
    'process_ir_ingresos_totales',
    'process_ir_activos_totales',
    'process_ir_utilidad',
]
