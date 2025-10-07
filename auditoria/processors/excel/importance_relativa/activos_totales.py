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
