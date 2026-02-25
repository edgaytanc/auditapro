from copy import copy


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
    balances_anuales = {k: v for k,
                        v in balances.items() if k.startswith('ANUAL-')}

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
                    partes = key.split(f"{seccion}-", 1)
                    if len(partes) > 1:
                        cuenta = partes[1]
                        # Evitar agregar cuentas vacías
                        if cuenta.strip():
                            cuentas_año[cuenta] = valor
                        else:
                            # Cuenta vacía detectada; se ignora.
                            pass

            cuentas_por_seccion[seccion][año] = cuentas_año

    # Función auxiliar para copiar estilos
    def copiar_estilo(celda_origen, celda_destino):
        if celda_origen and celda_destino:
            # Copiar fuente, alineación, borde, relleno y formato numérico
            if celda_origen.font:
                celda_destino.font = copy(celda_origen.font)
            if celda_origen.border:
                celda_destino.border = copy(celda_origen.border)
            if celda_origen.fill:
                celda_destino.fill = copy(celda_origen.fill)
            if celda_origen.alignment:
                celda_destino.alignment = copy(celda_origen.alignment)
            if celda_origen.number_format:
                celda_destino.number_format = celda_origen.number_format

    # Función para actualizar fórmulas en un rango de columnas
    def actualizar_formulas_fila(sheet, fila, fila_inicio, fila_fin, columnas_a_actualizar):
        for col in columnas_a_actualizar:
            celda = sheet.cell(row=fila, column=col)
            if celda.data_type == 'f':
                nueva_formula = f"=SUM({sheet.cell(row=fila_inicio, column=col).coordinate}:{sheet.cell(row=fila_fin, column=col).coordinate})"
                celda.value = nueva_formula
                # Fórmula actualizada

    # Procesar cada hoja del libro que tenga "BALANCE" o "BG" en su título
    for sheet in workbook.worksheets:
        if "BALANCE" in sheet.title.upper() or "BG" in sheet.title.upper():
            # Procesando hoja: {sheet.title}

            # Buscar las celdas clave en la hoja
            fila_activo = None
            fila_suma_activo = None
            fila_pasivo_patrimonio = None
            fila_suma_pasivo_patrimonio = None

            # Buscar las secciones y filas de suma
            for row_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=100, min_col=2, max_col=2), 1):
                cell = row[0]  # Columna B
                if cell.value and isinstance(cell.value, str):
                    if cell.value == "ACTIVO":
                        fila_activo = row_idx
                    elif "SUMA" in cell.value.upper() and "ACTIVO" in cell.value.upper():
                        fila_suma_activo = row_idx
                    elif cell.value == "PASIVO Y PATRIMONIO":
                        fila_pasivo_patrimonio = row_idx
                    elif "SUMA" in cell.value.upper() and "PASIVO" in cell.value.upper() and "PATRIMONIO" in cell.value.upper():
                        fila_suma_pasivo_patrimonio = row_idx

            # Verificar si encontramos las secciones necesarias
            if not fila_activo or not fila_pasivo_patrimonio:
                # No se encontraron las secciones requeridas en la hoja
                continue

            # Si no encontramos la fila de suma de activo, buscar la fila anterior a PASIVO Y PATRIMONIO
            if not fila_suma_activo and fila_pasivo_patrimonio:
                fila_suma_activo = fila_pasivo_patrimonio - 1

            # Si no encontramos la fila de suma de pasivo y patrimonio, buscar en las últimas filas
            if not fila_suma_pasivo_patrimonio:
                for row_idx, row in enumerate(sheet.iter_rows(min_row=fila_pasivo_patrimonio, max_row=fila_pasivo_patrimonio + 20, min_col=2, max_col=2), fila_pasivo_patrimonio):
                    cell = row[0]
                    if cell.value and isinstance(cell.value, str) and "SUMA" in cell.value.upper():
                        fila_suma_pasivo_patrimonio = row_idx
                        break

            # Si aún no encontramos la fila de suma, tomar una aproximación
            if not fila_suma_pasivo_patrimonio:
                # No se encontró la fila de suma de pasivo y patrimonio, usando aproximación
                # Usar una fila aproximada si no se encuentra explícitamente
                fila_suma_pasivo_patrimonio = fila_pasivo_patrimonio + 10

            # Secciones encontradas: Activo, Pasivo y Patrimonio

            # Obtener los años para las columnas
            if len(años_ordenados) >= 2:
                año_anterior = años_ordenados[1]  # El segundo año más reciente
                año_actual = años_ordenados[0]    # El año más reciente

                # === PROCESAMIENTO DE ACTIVO ===
                # Calcular espacio disponible vs necesario para ACTIVO
                espacio_disponible_activo = fila_suma_activo - \
                    (fila_activo + 1)
                cuentas_activo = cuentas_por_seccion['Activo'][año_actual]
                cuentas_necesarias_activo = len(cuentas_activo)

                # Info cálculo de espacio para Activo

                # Insertar filas si es necesario
                filas_a_insertar_activo = max(
                    0, cuentas_necesarias_activo - espacio_disponible_activo)
                if filas_a_insertar_activo > 0:
                    # Insertando filas para Activo

                    # Guardar estilos de la fila que usaremos como modelo (justo antes de la suma)
                    fila_modelo = fila_suma_activo - 1
                    estilos_modelo = {}
                    for col in range(1, sheet.max_column + 1):
                        celda_modelo = sheet.cell(row=fila_modelo, column=col)
                        estilos_modelo[col] = {
                            'font': copy(celda_modelo.font) if celda_modelo.font else None,
                            'border': copy(celda_modelo.border) if celda_modelo.border else None,
                            'fill': copy(celda_modelo.fill) if celda_modelo.fill else None,
                            'alignment': copy(celda_modelo.alignment) if celda_modelo.alignment else None,
                            'number_format': celda_modelo.number_format
                        }

                    # Insertar filas justo antes de la fila de suma
                    for _ in range(filas_a_insertar_activo):
                        sheet.insert_rows(fila_suma_activo)

                        # Aplicar estilos a la fila recién insertada
                        for col in range(1, sheet.max_column + 1):
                            celda_nueva = sheet.cell(
                                row=fila_suma_activo, column=col)
                            celda_modelo = sheet.cell(
                                row=fila_modelo, column=col)
                            copiar_estilo(celda_modelo, celda_nueva)

                    # Ajustar las referencias a filas posteriores
                    fila_suma_activo += filas_a_insertar_activo
                    fila_pasivo_patrimonio += filas_a_insertar_activo
                    fila_suma_pasivo_patrimonio += filas_a_insertar_activo

                # Actualizar las fórmulas para ACTIVO (solo columnas C y D)
                columnas_a_actualizar = [3, 4]  # C y D solamente
                fila_inicio_activo = fila_activo + 1
                fila_fin_activo = fila_suma_activo - 1

                actualizar_formulas_fila(
                    sheet, fila_suma_activo, fila_inicio_activo, fila_fin_activo, columnas_a_actualizar)

                # Llenar los valores de ACTIVO
                fila_actual = fila_activo + 1

                # Insertar las cuentas de ACTIVO
                for cuenta, valor_actual in cuentas_activo.items():
                    # Insertar el nombre de la cuenta en la columna B
                    sheet.cell(row=fila_actual, column=2).value = cuenta
                    # Insertando cuenta ACTIVO

                    # Insertar el valor del año anterior en la columna C
                    valor_anterior = cuentas_por_seccion['Activo'][año_anterior].get(
                        cuenta, 0)
                    celda_anterior = sheet.cell(row=fila_actual, column=3)
                    if not celda_anterior.data_type == 'f':  # No es una fórmula
                        celda_anterior.value = valor_anterior
                    # Valor anterior registrado

                    # Insertar el valor del año actual en la columna D
                    celda_actual = sheet.cell(row=fila_actual, column=4)
                    if not celda_actual.data_type == 'f':  # No es una fórmula
                        celda_actual.value = valor_actual
                    # Valor actual registrado

                    # Asignar fórmulas en columnas E y F para la fila actual
                    celda_e = sheet.cell(row=fila_actual, column=5)
                    celda_e.value = f"=D{fila_actual}-C{fila_actual}"
                    celda_f = sheet.cell(row=fila_actual, column=6)
                    celda_f.value = f"=D{fila_actual}/D{fila_suma_activo}"
                    # Fórmulas asignadas E y F

                    fila_actual += 1

                # === PROCESAMIENTO DE PASIVO Y PATRIMONIO ===
                # Calcular espacio disponible vs necesario para PASIVO y PATRIMONIO
                espacio_disponible_pp = fila_suma_pasivo_patrimonio - \
                    (fila_pasivo_patrimonio + 1)
                cuentas_pasivo = cuentas_por_seccion['Pasivo'][año_actual]
                cuentas_patrimonio = cuentas_por_seccion['Patrimonio'][año_actual]
                cuentas_necesarias_pp = len(
                    cuentas_pasivo) + len(cuentas_patrimonio)

                # Info cálculo de espacio para Pasivo y Patrimonio

                # Insertar filas si es necesario
                filas_a_insertar_pp = max(
                    0, cuentas_necesarias_pp - espacio_disponible_pp)
                if filas_a_insertar_pp > 0:
                    # Insertando filas para Pasivo y Patrimonio

                    # Guardar estilos de la fila que usaremos como modelo (justo antes de la suma)
                    fila_modelo = fila_suma_pasivo_patrimonio - 1
                    estilos_modelo = {}
                    for col in range(1, sheet.max_column + 1):
                        celda_modelo = sheet.cell(row=fila_modelo, column=col)
                        estilos_modelo[col] = {
                            'font': copy(celda_modelo.font) if celda_modelo.font else None,
                            'border': copy(celda_modelo.border) if celda_modelo.border else None,
                            'fill': copy(celda_modelo.fill) if celda_modelo.fill else None,
                            'alignment': copy(celda_modelo.alignment) if celda_modelo.alignment else None,
                            'number_format': celda_modelo.number_format
                        }

                    # Insertar filas justo antes de la fila de suma
                    for _ in range(filas_a_insertar_pp):
                        sheet.insert_rows(fila_suma_pasivo_patrimonio)

                        # Aplicar estilos a la fila recién insertada
                        for col in range(1, sheet.max_column + 1):
                            celda_nueva = sheet.cell(
                                row=fila_suma_pasivo_patrimonio, column=col)
                            celda_modelo = sheet.cell(
                                row=fila_modelo, column=col)
                            copiar_estilo(celda_modelo, celda_nueva)

                    # Ajustar las referencias a filas posteriores
                    fila_suma_pasivo_patrimonio += filas_a_insertar_pp

                # Actualizar las fórmulas para PASIVO Y PATRIMONIO (solo columnas C y D)
                columnas_a_actualizar = [3, 4]  # C y D solamente
                fila_inicio_pp = fila_pasivo_patrimonio + 1
                fila_fin_pp = fila_suma_pasivo_patrimonio - 1

                actualizar_formulas_fila(
                    sheet, fila_suma_pasivo_patrimonio, fila_inicio_pp, fila_fin_pp, columnas_a_actualizar)

                # Llenar los valores de PASIVO y PATRIMONIO
                fila_actual = fila_pasivo_patrimonio + 1

                # Insertar las cuentas de PASIVO
                for cuenta, valor_actual in cuentas_pasivo.items():
                    sheet.cell(row=fila_actual, column=2).value = cuenta
                    # Insertando cuenta PASIVO/PATRIMONIO

                    # Insertar el valor del año anterior en la columna C
                    valor_anterior = cuentas_por_seccion['Pasivo'][año_anterior].get(
                        cuenta, 0)
                    celda_anterior = sheet.cell(row=fila_actual, column=3)
                    if not celda_anterior.data_type == 'f':
                        celda_anterior.value = valor_anterior
                    # Valor anterior registrado

                    # Insertar el valor del año actual en la columna D
                    celda_actual = sheet.cell(row=fila_actual, column=4)
                    if not celda_actual.data_type == 'f':
                        celda_actual.value = valor_actual
                    # Valor actual registrado

                    # Asignar fórmulas E y F
                    celda_e = sheet.cell(row=fila_actual, column=5)
                    celda_e.value = f"=D{fila_actual}-C{fila_actual}"
                    celda_f = sheet.cell(row=fila_actual, column=6)
                    celda_f.value = f"=D{fila_actual}/D{fila_suma_pasivo_patrimonio}"
                    # Fórmulas asignadas E y F

                    fila_actual += 1

                # Insertar las cuentas de PATRIMONIO (continuar en la misma secuencia)
                for cuenta, valor_actual in cuentas_patrimonio.items():
                    sheet.cell(row=fila_actual, column=2).value = cuenta
                    # Insertando cuenta PASIVO/PATRIMONIO

                    # Insertar el valor del año anterior en la columna C
                    valor_anterior = cuentas_por_seccion['Patrimonio'][año_anterior].get(
                        cuenta, 0)
                    celda_anterior = sheet.cell(row=fila_actual, column=3)
                    if not celda_anterior.data_type == 'f':
                        celda_anterior.value = valor_anterior
                    # Valor anterior registrado

                    # Insertar el valor del año actual en la columna D
                    celda_actual = sheet.cell(row=fila_actual, column=4)
                    if not celda_actual.data_type == 'f':
                        celda_actual.value = valor_actual
                    # Valor actual registrado

                    # Asignar fórmulas E y F
                    celda_e = sheet.cell(row=fila_actual, column=5)
                    celda_e.value = f"=D{fila_actual}-C{fila_actual}"
                    celda_f = sheet.cell(row=fila_actual, column=6)
                    celda_f.value = f"=D{fila_actual}/D{fila_suma_pasivo_patrimonio}"
                    # Fórmulas asignadas E y F

                    fila_actual += 1
    return workbook
