def process_horizontal_vertical_analysis(workbook, balances):
    """
    Procesa el archivo de análisis horizontal y vertical
    
    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros
    
    Returns:
        El libro de Excel procesado
    """
    # Filtrar solo las cuentas de tipo ANUAL
    balances_anuales = {k: v for k, v in balances.items() if k.startswith('ANUAL-')}
    
    # Verificar si hay cuentas anuales
    if not balances_anuales:
        return workbook
    
    # Extraer todos los años disponibles en los balances anuales
    años = set()
    for key in balances_anuales.keys():
        partes = key.split('-')
        if len(partes) >= 2:
            año = partes[1]
            if año.isdigit():  # Asegurarse de que es un año válido
                años.add(año)
    
    # Ordenar los años de más reciente a más antiguo
    años_ordenados = sorted(años, reverse=True)
    
    # Extraer las secciones que nos interesan (ACTIVO, PASIVO, PATRIMONIO)
    secciones_interes = ['Activo', 'Pasivo', 'Patrimonio']
    
    # Estructura para almacenar las cuentas por sección y año
    cuentas_por_seccion = {}
    
    # Extraer las cuentas de las secciones de interés
    for seccion in secciones_interes: 
        cuentas_por_seccion[seccion] = {}
        
        for año in años_ordenados[:2]:  # Solo los dos años más recientes
            cuentas_año = {}
            
            for key, valor in balances_anuales.items():
                if año in key and seccion in key:
                    # Extraer la cuenta después de la sección
                    partes = key.split(f"{seccion}-")
                    if len(partes) > 1:
                        cuenta = partes[1]
                        cuentas_año[cuenta] = valor
            
            cuentas_por_seccion[seccion][año] = cuentas_año
    
    # Implementar el análisis horizontal y vertical
    for sheet in workbook.worksheets:
        # Buscar la celda que contiene "ACTIVO" en la columna B
        fila_activo = None
        fila_pasivo_patrimonio = None
        
        # Buscar las celdas clave en la hoja
        for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=100, min_col=2, max_col=2), 1):
            cell = row[0]  # Columna B
            if cell.value == "ACTIVO":
                fila_activo = row_idx
            elif cell.value == "PASIVO Y PATRIMONIO":
                fila_pasivo_patrimonio = row_idx
        
        if not fila_activo:
            continue
        
        # Obtener los años para las columnas C y D
        if len(años_ordenados) >= 2:
            año_anterior = años_ordenados[1]  # El segundo año más reciente
            año_actual = años_ordenados[0]    # El año más reciente
            
            # Llenar los valores de ACTIVO
            fila_actual = fila_activo + 1  # Empezar en la fila siguiente a "ACTIVO"
            
            # Insertar las cuentas de ACTIVO
            for cuenta, valor_actual in cuentas_por_seccion['Activo'][año_actual].items():
                # Insertar el nombre de la cuenta en la columna B
                sheet.cell(row=fila_actual, column=2).value = cuenta
                
                # Insertar el valor del año anterior en la columna C si no tiene fórmula
                valor_anterior = cuentas_por_seccion['Activo'][año_anterior].get(cuenta, 0)
                celda_anterior = sheet.cell(row=fila_actual, column=3)
                if not celda_anterior.data_type == 'f':  # No es una fórmula
                    celda_anterior.value = valor_anterior
                
                # Insertar el valor del año actual en la columna D si no tiene fórmula
                celda_actual = sheet.cell(row=fila_actual, column=4)
                if not celda_actual.data_type == 'f':  # No es una fórmula
                    celda_actual.value = valor_actual
                
                fila_actual += 1
            
            # Si encontramos la sección de PASIVO Y PATRIMONIO, llenarla también
            if fila_pasivo_patrimonio:
                fila_actual = fila_pasivo_patrimonio + 1  # Empezar en la fila siguiente a "PASIVO Y PATRIMONIO"
                
                # Insertar las cuentas de PASIVO
                for cuenta, valor_actual in cuentas_por_seccion['Pasivo'][año_actual].items():
                    sheet.cell(row=fila_actual, column=2).value = cuenta
                    
                    valor_anterior = cuentas_por_seccion['Pasivo'][año_anterior].get(cuenta, 0)
                    celda_anterior = sheet.cell(row=fila_actual, column=3)
                    if not celda_anterior.data_type == 'f':
                        celda_anterior.value = valor_anterior
                    
                    celda_actual = sheet.cell(row=fila_actual, column=4)
                    if not celda_actual.data_type == 'f':
                        celda_actual.value = valor_actual
                    
                    fila_actual += 1
                
                # Insertar las cuentas de PATRIMONIO
                for cuenta, valor_actual in cuentas_por_seccion['Patrimonio'][año_actual].items():
                    sheet.cell(row=fila_actual, column=2).value = cuenta
                    
                    valor_anterior = cuentas_por_seccion['Patrimonio'][año_anterior].get(cuenta, 0)
                    celda_anterior = sheet.cell(row=fila_actual, column=3)
                    if not celda_anterior.data_type == 'f':
                        celda_anterior.value = valor_anterior
                    
                    celda_actual = sheet.cell(row=fila_actual, column=4)
                    if not celda_actual.data_type == 'f':
                        celda_actual.value = valor_actual
                    
                    fila_actual += 1
    return workbook