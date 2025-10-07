from .utils import copiar_estilo, actualizar_formulas_fila

def procesar_hoja_balance(sheet, cuentas_por_seccion, años_ordenados):
    """Procesa una única hoja de balance, insertando y actualizando datos."""
    # Buscar las celdas clave en la hoja
    fila_activo, fila_suma_activo, fila_pasivo_patrimonio, fila_suma_pasivo_patrimonio = _buscar_secciones(sheet)

    if not fila_activo or not fila_pasivo_patrimonio:
        return

    if not fila_suma_activo:
        fila_suma_activo = fila_pasivo_patrimonio - 1
    if not fila_suma_pasivo_patrimonio:
        fila_suma_pasivo_patrimonio = fila_pasivo_patrimonio + 10

    año_actual, año_anterior = años_ordenados[0], años_ordenados[1]

    # Procesar ACTIVO
    filas_insertadas_activo = _procesar_seccion(
        sheet, 'Activo', fila_activo, fila_suma_activo, 
        cuentas_por_seccion, año_actual, año_anterior
    )
    
    # Ajustar filas de secciones posteriores
    fila_pasivo_patrimonio += filas_insertadas_activo
    fila_suma_pasivo_patrimonio += filas_insertadas_activo

    # Procesar PASIVO y PATRIMONIO
    _procesar_seccion_combinada(
        sheet, ['Pasivo', 'Patrimonio'], fila_pasivo_patrimonio, fila_suma_pasivo_patrimonio, 
        cuentas_por_seccion, año_actual, año_anterior
    )

def _buscar_secciones(sheet):
    """Busca y devuelve las filas clave de las secciones del balance."""
    fila_activo, fila_suma_activo, fila_pasivo_patrimonio, fila_suma_pasivo_patrimonio = None, None, None, None
    for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=100, min_col=2, max_col=2), 1):
        cell_value = row[0].value
        if isinstance(cell_value, str):
            if cell_value == "ACTIVO":
                fila_activo = row_idx
            elif "SUMA" in cell_value.upper() and "ACTIVO" in cell_value.upper():
                fila_suma_activo = row_idx
            elif cell_value == "PASIVO Y PATRIMONIO":
                fila_pasivo_patrimonio = row_idx
            elif "SUMA" in cell_value.upper() and "PASIVO" in cell_value.upper() and "PATRIMONIO" in cell_value.upper():
                fila_suma_pasivo_patrimonio = row_idx
    return fila_activo, fila_suma_activo, fila_pasivo_patrimonio, fila_suma_pasivo_patrimonio

def _procesar_seccion(sheet, seccion, fila_seccion, fila_suma, cuentas_por_seccion, año_actual, año_anterior):
    """Procesa una sección individual del balance (ej. Activo)."""
    cuentas = cuentas_por_seccion[seccion][año_actual]
    filas_insertadas = _insertar_filas_si_es_necesario(sheet, fila_seccion + 1, fila_suma, len(cuentas))
    fila_suma += filas_insertadas

    actualizar_formulas_fila(sheet, fila_suma, fila_seccion + 1, fila_suma - 1, [3, 4])

    fila_actual = fila_seccion + 1
    for cuenta, valor_actual in cuentas.items():
        valor_anterior = cuentas_por_seccion[seccion][año_anterior].get(cuenta, 0)
        _llenar_fila_datos(sheet, fila_actual, cuenta, valor_actual, valor_anterior, fila_suma)
        fila_actual += 1
        
    return filas_insertadas

def _procesar_seccion_combinada(sheet, secciones, fila_seccion, fila_suma, cuentas_por_seccion, año_actual, año_anterior):
    """Procesa secciones combinadas (Pasivo y Patrimonio)."""
    cuentas_combinadas = {k: v for sec in secciones for k, v in cuentas_por_seccion[sec][año_actual].items()}
    filas_insertadas = _insertar_filas_si_es_necesario(sheet, fila_seccion + 1, fila_suma, len(cuentas_combinadas))
    fila_suma += filas_insertadas

    actualizar_formulas_fila(sheet, fila_suma, fila_seccion + 1, fila_suma - 1, [3, 4])

    fila_actual = fila_seccion + 1
    for seccion in secciones:
        for cuenta, valor_actual in cuentas_por_seccion[seccion][año_actual].items():
            valor_anterior = cuentas_por_seccion[seccion][año_anterior].get(cuenta, 0)
            _llenar_fila_datos(sheet, fila_actual, cuenta, valor_actual, valor_anterior, fila_suma)
            fila_actual += 1

def _insertar_filas_si_es_necesario(sheet, fila_inicio, fila_fin, cuentas_necesarias):
    """Inserta filas en la hoja si el espacio no es suficiente."""
    espacio_disponible = fila_fin - fila_inicio
    filas_a_insertar = max(0, cuentas_necesarias - espacio_disponible)
    if filas_a_insertar > 0:
        fila_modelo = fila_fin - 1
        for _ in range(filas_a_insertar):
            sheet.insert_rows(fila_fin)
            for col in range(1, sheet.max_column + 1):
                copiar_estilo(sheet.cell(row=fila_modelo, column=col), sheet.cell(row=fila_fin, column=col))
    return filas_a_insertar

def _llenar_fila_datos(sheet, fila, cuenta, valor_actual, valor_anterior, fila_suma_seccion):
    """Llena los datos y fórmulas para una fila de cuenta."""
    sheet.cell(row=fila, column=2).value = cuenta
    if not sheet.cell(row=fila, column=3).data_type == 'f':
        sheet.cell(row=fila, column=3).value = valor_anterior
    if not sheet.cell(row=fila, column=4).data_type == 'f':
        sheet.cell(row=fila, column=4).value = valor_actual
    
    sheet.cell(row=fila, column=5).value = f"=D{fila}-C{fila}"
    sheet.cell(row=fila, column=6).value = f"=D{fila}/D{fila_suma_seccion}"
