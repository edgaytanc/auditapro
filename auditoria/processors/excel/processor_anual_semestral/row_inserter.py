from .utils import copiar_estilo_fila, buscar_filas_clave, encontrar_fila_cuenta_normal, _actualizar_formula_suma, _columnas_valores

def insertar_cuentas_en_hoja(sheet, cuentas_por_seccion, tipo_balance, fechas, balances):
    """Inserta las cuentas en las posiciones correctas de la hoja Excel."""
    filas = buscar_filas_clave(sheet)
    fila_balance_general = filas['BALANCE GENERAL']
    fila_total_activo = filas['TOTAL ACTIVO']
    fila_total_pasivo_patrimonio = filas['TOTAL PASIVO Y PATRIMONIO']

    # 1. Insertar ACTIVO
    fila_actual, fila_total_activo, fila_estilo = _insertar_seccion_cuentas(
        sheet, 'Activo', cuentas_por_seccion['Activo'], tipo_balance, fechas, balances,
        fila_balance_general + 1, fila_total_activo, fila_balance_general
    )
    cols_valores = _columnas_valores(tipo_balance, fechas)
    _actualizar_formula_suma(sheet, fila_total_activo, cols_valores, fila_balance_general + 1, fila_total_activo - 1)

    # Ajustar filas posteriores
    filas_insertadas_activo = fila_total_activo - filas['TOTAL ACTIVO']
    fila_total_pasivo_patrimonio += filas_insertadas_activo

    # 2. Insertar PASIVO y PATRIMONIO
    fila_actual = fila_total_activo + 1
    fila_actual, fila_total_pasivo_patrimonio, _ = _insertar_seccion_cuentas(
        sheet, 'Pasivo', cuentas_por_seccion['Pasivo'], tipo_balance, fechas, balances,
        fila_actual, fila_total_pasivo_patrimonio, fila_total_activo
    )
    fila_actual, fila_total_pasivo_patrimonio, _ = _insertar_seccion_cuentas(
        sheet, 'Patrimonio', cuentas_por_seccion['Patrimonio'], tipo_balance, fechas, balances,
        fila_actual, fila_total_pasivo_patrimonio, fila_actual - 1
    )
    _actualizar_formula_suma(sheet, fila_total_pasivo_patrimonio, cols_valores, fila_total_activo + 1, fila_total_pasivo_patrimonio - 1)

    # 3. Insertar ESTADO DE RESULTADOS
    _insertar_estado_resultados(sheet, cuentas_por_seccion['ESTADO DE RESULTADOS'], tipo_balance, fechas, balances, fila_total_pasivo_patrimonio + 1, fila_balance_general)

def _insertar_seccion_cuentas(sheet, seccion, cuentas, tipo_balance, fechas, balances, fila_inicio, fila_limite, fila_estilo):
    """Inserta cuentas de una sección, gestionando la inserción de filas."""
    fila_actual = fila_inicio
    for cuenta in cuentas:
        if fila_actual >= fila_limite:
            sheet.insert_rows(fila_actual)
            copiar_estilo_fila(sheet, fila_estilo, fila_actual)
            fila_limite += 1
        
        sheet.cell(row=fila_actual, column=2).value = cuenta
        _insertar_valores_fila(sheet, fila_actual, tipo_balance, fechas, seccion, cuenta, balances)
        
        fila_estilo = fila_actual
        fila_actual += 1

    return fila_actual, fila_limite, fila_estilo

def _insertar_estado_resultados(sheet, cuentas, tipo_balance, fechas, balances, fila_inicio, fila_referencia_estilo):
    """Inserta las cuentas de ESTADO DE RESULTADOS al final."""
    fila_actual = fila_inicio
    fila_cuenta_normal = encontrar_fila_cuenta_normal(sheet, fila_referencia_estilo + 1, sheet.max_row) or fila_referencia_estilo + 1

    espacio_disponible = sheet.max_row - fila_actual
    if espacio_disponible < len(cuentas):
        for _ in range(len(cuentas) - espacio_disponible):
            sheet.insert_rows(fila_actual)
            copiar_estilo_fila(sheet, fila_cuenta_normal, fila_actual)

    for cuenta in cuentas:
        sheet.cell(row=fila_actual, column=2).value = cuenta
        _insertar_valores_fila(sheet, fila_actual, tipo_balance, fechas, 'ESTADO DE RESULTADOS', cuenta, balances)
        copiar_estilo_fila(sheet, fila_cuenta_normal, fila_actual)
        fila_actual += 1

def _insertar_valores_fila(sheet, fila, tipo_balance, fechas, seccion, cuenta, balances):
    """Inserta los valores para una cuenta en una fila específica."""
    if tipo_balance == 'ANUAL' and fechas:
        if len(fechas) > 0:
            _insertar_valor_celda(sheet, fila, 3, tipo_balance, fechas[-1], seccion, cuenta, balances)
        if len(fechas) > 1:
            _insertar_valor_celda(sheet, fila, 4, tipo_balance, fechas[-2], seccion, cuenta, balances)
    elif tipo_balance == 'SEMESTRAL':
        for i, fecha in enumerate(fechas):
            if (columna := 3 + i) <= sheet.max_column:
                _insertar_valor_celda(sheet, fila, columna, tipo_balance, fecha, seccion, cuenta, balances)

def _insertar_valor_celda(sheet, fila, columna, tipo_balance, fecha, seccion, cuenta, balances):
    """Función helper para insertar un valor en una celda."""
    clave = f"{tipo_balance}-{fecha}-{seccion}-{cuenta}"
    if clave in balances:
        sheet.cell(row=fila, column=columna).value = balances[clave]
