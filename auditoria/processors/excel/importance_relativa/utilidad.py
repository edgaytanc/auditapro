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
