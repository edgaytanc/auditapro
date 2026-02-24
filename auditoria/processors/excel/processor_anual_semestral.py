from copy import copy


def formatear_fecha(fecha_str):
    """Formatea una fecha en formato YYYY-MM-DD a 'Al DD/MM/YYYY'"""
    try:
        partes = fecha_str.split('-')
        if len(partes) >= 3:
            return f"Al {partes[2]}/{partes[1]}/{partes[0]}"
        return fecha_str
    except Exception:
        return fecha_str


def clasificar_cuentas_por_seccion(balances, tipo_balance):
    """Clasifica las cuentas del balance por sección."""
    cuentas_por_seccion = {
        'Activo': [],
        'Pasivo': [],
        'Patrimonio': [],
        'ESTADO DE RESULTADOS': []
    }

    # Extraer cuentas únicas por sección
    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 5:
            tipo, seccion = partes[0], partes[4]
            cuenta = '-'.join(partes[5:])  # La cuenta puede tener guiones
            # Solo procesar las cuentas del tipo de balance especificado
            if tipo == tipo_balance and seccion in cuentas_por_seccion and cuenta not in cuentas_por_seccion[seccion]:
                cuentas_por_seccion[seccion].append(cuenta)

    # Ordenar cuentas dentro de cada sección
    for seccion in cuentas_por_seccion:
        cuentas_por_seccion[seccion].sort()

    return cuentas_por_seccion


def copiar_estilo_fila(sheet, fila_origen, fila_destino, columnas=None):
    """Copia el estilo completo de una fila a otra."""
    if columnas is None:
        columnas = range(1, sheet.max_column + 1)

    for col in columnas:
        celda_origen = sheet.cell(row=fila_origen, column=col)
        celda_destino = sheet.cell(row=fila_destino, column=col)

        try:
            for attr in ['border', 'font', 'fill', 'alignment', 'number_format']:
                valor = getattr(celda_origen, attr, None)
                if valor:
                    setattr(celda_destino, attr, copy(valor)
                            if attr != 'number_format' else valor)
        except Exception:
            pass


def insertar_valor_en_celda(sheet, fila, columna, tipo_balance, fecha, seccion, cuenta, balances):
    """Inserta un valor en una celda según el tipo de balance, fecha, sección y cuenta."""
    clave = f"{tipo_balance}-{fecha}-{seccion}-{cuenta}"
    if clave in balances:
        sheet.cell(row=fila, column=columna).value = balances[clave]
        return True
    return False


def buscar_filas_clave(sheet):
    """Busca las filas clave en la hoja Excel."""
    filas = {'BALANCE GENERAL': None, 'TOTAL ACTIVO': None,
             'TOTAL PASIVO Y PATRIMONIO': None}

    # Buscar en columna B primero
    for i in range(1, sheet.max_row + 1):
        valor_celda = str(sheet.cell(row=i, column=2).value).upper(
        ) if sheet.cell(row=i, column=2).value else ""
        for clave in filas:
            if clave in valor_celda:
                filas[clave] = i

    # Si no se encontraron todas, buscar en columna A
    if not all(filas.values()):
        for i in range(1, sheet.max_row + 1):
            if all(filas.values()):
                break

            valor_celda = str(sheet.cell(row=i, column=1).value).upper(
            ) if sheet.cell(row=i, column=1).value else ""

            if filas['BALANCE GENERAL'] is None and "BALANCE" in valor_celda:
                filas['BALANCE GENERAL'] = i
            elif filas['TOTAL ACTIVO'] is None and "TOTAL" in valor_celda and "ACTIVO" in valor_celda:
                filas['TOTAL ACTIVO'] = i
            elif filas['TOTAL PASIVO Y PATRIMONIO'] is None and "TOTAL" in valor_celda and ("PASIVO" in valor_celda or "PATRIMONIO" in valor_celda):
                filas['TOTAL PASIVO Y PATRIMONIO'] = i

    # Valores predeterminados si no se encontraron
    return {
        'BALANCE GENERAL': filas['BALANCE GENERAL'] or 14,
        'TOTAL ACTIVO': filas['TOTAL ACTIVO'] or 22,
        'TOTAL PASIVO Y PATRIMONIO': filas['TOTAL PASIVO Y PATRIMONIO'] or 26
    }


def encontrar_fila_cuenta_normal(sheet, fila_inicio, fila_fin):
    """Encuentra una fila de cuenta normal para usar como referencia de estilo."""
    for i in range(fila_inicio, fila_fin):
        valor_celda = str(sheet.cell(row=i, column=2).value).upper(
        ) if sheet.cell(row=i, column=2).value else ""
        if valor_celda and "TOTAL" not in valor_celda:
            return i
    return None


def insertar_seccion_cuentas(sheet, seccion, cuentas, tipo_balance, fechas, balances, fila_inicio, fila_limite, fila_estilo):
    """Inserta cuentas de una sección específica en la hoja Excel."""
    fila_actual = fila_inicio

    for cuenta in cuentas:
        # Si llegamos al límite, insertar una fila nueva
        if fila_actual >= fila_limite:
            sheet.insert_rows(fila_actual)
            copiar_estilo_fila(sheet, fila_estilo, fila_actual)
            fila_limite += 1

        # Insertar nombre de cuenta en columna B
        sheet.cell(row=fila_actual, column=2).value = cuenta

        # Insertar valores según el tipo de balance
        if tipo_balance == 'ANUAL' and fechas:
            # Año actual (última fecha)
            insertar_valor_en_celda(
                sheet, fila_actual, 3, tipo_balance, fechas[-1], seccion, cuenta, balances)

            # Año anterior (penúltima fecha, si existe)
            if len(fechas) >= 2:
                insertar_valor_en_celda(
                    sheet, fila_actual, 4, tipo_balance, fechas[-2], seccion, cuenta, balances)

        # Para SEMESTRAL, insertar valores para todas las fechas disponibles
        elif tipo_balance == 'SEMESTRAL':
            for i, fecha in enumerate(fechas):
                columna = 3 + i  # Empezar desde la columna C
                if columna <= sheet.max_column:
                    insertar_valor_en_celda(
                        sheet, fila_actual, columna, tipo_balance, fecha, seccion, cuenta, balances)

        # Actualizar la fila de estilo y avanzar a la siguiente fila
        fila_estilo = fila_actual
        fila_actual += 1

    return fila_actual, fila_limite, fila_estilo


def _columnas_valores(tipo_balance: str, fechas: list):
    """Devuelve la lista de índices de columnas que contienen valores."""
    if tipo_balance == "ANUAL":
        # Máximo dos columnas (año actual y anterior)
        return list(range(3, 3 + min(2, len(fechas))))
    else:  # SEMESTRAL
        return list(range(3, 3 + len(fechas)))


def _actualizar_formula_suma(sheet, fila_suma: int, columnas: list[int], fila_inicio: int, fila_fin: int):
    """Reescribe la fórmula de suma en la fila dada para las columnas indicadas."""
    if fila_fin < fila_inicio:
        return  # nada que sumar

    for col in columnas:
        celda_inicio = sheet.cell(row=fila_inicio, column=col).coordinate
        celda_fin = sheet.cell(row=fila_fin, column=col).coordinate
        sheet.cell(row=fila_suma,
                   column=col).value = f"=SUM({celda_inicio}:{celda_fin})"


def insertar_cuentas_en_hoja(sheet, cuentas_por_seccion, tipo_balance, fechas, balances):
    """Inserta las cuentas en las posiciones correctas de la hoja Excel."""
    # Buscar las filas clave
    filas = buscar_filas_clave(sheet)
    fila_balance_general = filas['BALANCE GENERAL']
    fila_total_activo = filas['TOTAL ACTIVO']
    fila_total_pasivo_patrimonio = filas['TOTAL PASIVO Y PATRIMONIO']

    # 1. Insertar cuentas de ACTIVO
    fila_actual = fila_balance_general + 1
    fila_estilo = fila_balance_general

    fila_actual, fila_total_activo, fila_estilo = insertar_seccion_cuentas(
        sheet, 'Activo', cuentas_por_seccion['Activo'],
        tipo_balance, fechas, balances,
        fila_actual, fila_total_activo, fila_estilo
    )

    # Actualizar fórmula TOTAL ACTIVO
    cols_valores = _columnas_valores(tipo_balance, fechas)
    _actualizar_formula_suma(
        sheet,
        fila_total_activo,
        cols_valores,
        fila_balance_general + 1,
        fila_total_activo - 1,
    )

    # Actualizar fila_total_pasivo_patrimonio si se insertaron filas en Activo
    fila_total_pasivo_patrimonio += (fila_total_activo - filas['TOTAL ACTIVO'])

    # 2. Insertar cuentas de PASIVO
    fila_actual = fila_total_activo + 1
    fila_estilo = fila_total_activo

    fila_actual, fila_total_pasivo_patrimonio, fila_estilo = insertar_seccion_cuentas(
        sheet, 'Pasivo', cuentas_por_seccion['Pasivo'],
        tipo_balance, fechas, balances,
        fila_actual, fila_total_pasivo_patrimonio, fila_estilo
    )

    # 3. Insertar cuentas de PATRIMONIO
    fila_actual, fila_total_pasivo_patrimonio, fila_estilo = insertar_seccion_cuentas(
        sheet, 'Patrimonio', cuentas_por_seccion['Patrimonio'],
        tipo_balance, fechas, balances,
        fila_actual, fila_total_pasivo_patrimonio, fila_estilo
    )

    # Actualizar fórmula TOTAL PASIVO Y PATRIMONIO
    _actualizar_formula_suma(
        sheet,
        fila_total_pasivo_patrimonio,
        cols_valores,
        fila_total_activo + 1,
        fila_total_pasivo_patrimonio - 1,
    )

    # 4. Insertar cuentas de ESTADO DE RESULTADOS
    fila_actual = fila_total_pasivo_patrimonio + 1

    # Buscar una fila de cuenta normal para usar como referencia de estilo
    fila_cuenta_normal = (
        encontrar_fila_cuenta_normal(sheet, fila_balance_general + 1, fila_total_activo) or
        encontrar_fila_cuenta_normal(sheet, fila_total_activo + 1, fila_total_pasivo_patrimonio) or
        fila_balance_general + 1
    )

    # Verificar si hay suficiente espacio para las cuentas de ESTADO DE RESULTADOS
    espacio_disponible = sheet.max_row - fila_actual
    cuentas_resultados = cuentas_por_seccion['ESTADO DE RESULTADOS']

    if espacio_disponible < len(cuentas_resultados):
        # Insertar filas necesarias
        for _ in range(len(cuentas_resultados) - espacio_disponible):
            sheet.insert_rows(fila_actual)
            copiar_estilo_fila(sheet, fila_cuenta_normal, fila_actual)

    # Insertar cuentas de ESTADO DE RESULTADOS
    for cuenta in cuentas_resultados:
        # Insertar nombre de cuenta en columna B
        sheet.cell(row=fila_actual, column=2).value = cuenta

        # Insertar valores según el tipo de balance
        if tipo_balance == 'ANUAL' and fechas:
            insertar_valor_en_celda(sheet, fila_actual, 3, tipo_balance,
                                    fechas[-1], 'ESTADO DE RESULTADOS', cuenta, balances)

            if len(fechas) >= 2:
                insertar_valor_en_celda(
                    sheet, fila_actual, 4, tipo_balance, fechas[-2], 'ESTADO DE RESULTADOS', cuenta, balances)

        elif tipo_balance == 'SEMESTRAL':
            for i, fecha in enumerate(fechas):
                columna = 3 + i
                if columna <= sheet.max_column:
                    insertar_valor_en_celda(
                        sheet, fila_actual, columna, tipo_balance, fecha, 'ESTADO DE RESULTADOS', cuenta, balances)

        # Copiar el estilo de la fila de cuenta normal
        copiar_estilo_fila(sheet, fila_cuenta_normal, fila_actual)
        fila_actual += 1


def process_anual_semestral_sheets(workbook, balances):
    """Procesa las hojas ANUAL y SEMESTRAL del Excel insertando las fechas."""
    # Extraer fechas de los balances
    fechas_anual = set()
    fechas_semestral = set()

    # Recolectar todas las fechas disponibles
    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 4:
            tipo_balance, fecha = partes[0], f"{partes[1]}-{partes[2]}-{partes[3]}"

            if tipo_balance == 'ANUAL':
                fechas_anual.add(fecha)
            elif tipo_balance == 'SEMESTRAL':
                fechas_semestral.add(fecha)

    # Convertir a listas y ordenar
    fechas_anual = sorted(list(fechas_anual))
    fechas_semestral = sorted(list(fechas_semestral))

    # Determinar fechas para ANUAL y formatear fechas para SEMESTRAL
    fecha_anual_actual = fechas_anual[-1] if fechas_anual else None
    fechas_semestral_formateadas = [
        formatear_fecha(f) for f in fechas_semestral]

    # Clasificar cuentas para ambos tipos de balance
    cuentas_anual = clasificar_cuentas_por_seccion(balances, 'ANUAL')
    cuentas_semestral = clasificar_cuentas_por_seccion(balances, 'SEMESTRAL')

    # Procesar cada hoja
    for sheet in workbook.worksheets:
        sheet_title = sheet.title.upper()

        # PROCESAR HOJA ANUAL/ACTUAL
        if sheet_title in ['ACTUAL', 'ANUAL'] and fecha_anual_actual:
            try:
                insertar_cuentas_en_hoja(
                    sheet, cuentas_anual, 'ANUAL', fechas_anual, balances)
            except Exception:
                pass

        # PROCESAR HOJA SEMESTRAL
        elif sheet_title == 'SEMESTRAL' and fechas_semestral:
            try:
                # Insertar fechas en la fila 14
                # Máximo 4 fechas (columnas C, D, E, F)
                for i, fecha in enumerate(fechas_semestral_formateadas[:4]):
                    sheet.cell(row=14, column=i+3).value = fecha

                # Insertar cuentas
                insertar_cuentas_en_hoja(
                    sheet, cuentas_semestral, 'SEMESTRAL', fechas_semestral, balances)
            except Exception:
                pass

    return workbook
