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
