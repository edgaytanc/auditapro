import logging

logger = logging.getLogger(__name__)

def process_ratios_financieros(workbook, balances):
    """
    Procesa las hojas de ratios financieros insertando las cuentas clasificadas por tipo y año.

    Args:
        workbook: Objeto workbook de openpyxl
        balances: Diccionario con los balances en formato:
                 ANUAL-YYYY-MM-DD-Seccion-Cuenta-TipoCuenta: valor
    """

    # Extraer fechas anuales disponibles
    fechas_anual = extraer_fechas_anuales(balances)

    if len(fechas_anual) < 2:
        return workbook

    # Ordenar fechas (más reciente primero)
    fechas_anual = sorted(fechas_anual, reverse=True)
    año_actual = fechas_anual[0]
    año_anterior = fechas_anual[1]

    # Clasificar cuentas por sección y tipo
    cuentas_clasificadas = clasificar_cuentas_por_seccion_y_tipo(
        balances, año_actual, año_anterior)

    # Procesar cada hoja relevante
    for sheet in workbook.worksheets:
        sheet_title = sheet.title.upper()

        if "ESTADOS FINANCIEROS COMPARATIVO" in sheet_title:
            procesar_hoja_comparativo(
                sheet, cuentas_clasificadas, año_actual, año_anterior)

        elif "ANÁLISIS VERTICAL" in sheet_title or "ANALISIS VERTICAL" in sheet_title:
            procesar_hoja_analisis_vertical(
                sheet, cuentas_clasificadas, año_actual, año_anterior)

    return workbook


def extraer_fechas_anuales(balances):
    """Extrae las fechas anuales únicas del diccionario balances"""
    fechas = set()
    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 4 and partes[0] == 'ANUAL':
            fecha = f"{partes[1]}-{partes[2]}-{partes[3]}"
            fechas.add(fecha)
    return sorted(list(fechas))


def clasificar_cuentas_por_seccion_y_tipo(balances, año_actual, año_anterior):
    """
    Clasifica las cuentas por sección y tipo, organizadas por año.

    Returns:
        dict: {
            'Activo': {
                'Corriente': {año_actual: {cuenta: valor}, año_anterior: {cuenta: valor}},
                'No Corriente': {año_actual: {cuenta: valor}, año_anterior: {cuenta: valor}}
            },
            'Pasivo': {...},
            'Patrimonio': {año_actual: {cuenta: valor}, año_anterior: {cuenta: valor}}
        }
    """
    estructura = {
        'Activo': {
            'Corriente': {año_actual: {}, año_anterior: {}},
            'No Corriente': {año_actual: {}, año_anterior: {}}
        },
        'Pasivo': {
            'Corriente': {año_actual: {}, año_anterior: {}},
            'No Corriente': {año_actual: {}, año_anterior: {}}
        },
        'Patrimonio': {año_actual: {}, año_anterior: {}},
        'ESTADO DE RESULTADOS': {año_actual: {}, año_anterior: {}}
    }

    for clave, valor in balances.items():
        partes = clave.split('-')
        if len(partes) >= 6 and partes[0] == 'ANUAL':
            fecha = f"{partes[1]}-{partes[2]}-{partes[3]}"
            seccion = partes[4]
            cuenta = partes[5]
            tipo_cuenta = partes[6]

            if fecha in [año_actual, año_anterior] and seccion in estructura:
                if seccion in ['Activo', 'Pasivo']:
                    if tipo_cuenta in ['Corriente', 'No Corriente']:
                        estructura[seccion][tipo_cuenta][fecha][cuenta] = valor
                elif seccion in ['Patrimonio', 'ESTADO DE RESULTADOS']:
                    estructura[seccion][fecha][cuenta] = valor

    return estructura


def encontrar_columnas_años(sheet):
    """Encuentra las columnas donde están 'Año actual' y 'Año anterior'"""
    columnas = {'año_actual': None, 'año_anterior': None}

    # Buscar en las primeras 10 filas
    for fila in range(1, 11):
        for col in range(1, 15):
            celda = sheet.cell(row=fila, column=col)
            if celda.value and isinstance(celda.value, str):
                valor = celda.value.strip().lower()
                if 'año actual' in valor:
                    columnas['año_actual'] = col
                elif 'año anterior' in valor:
                    columnas['año_anterior'] = col

    return columnas


def obtener_rangos_fijos_por_hoja(sheet_title):
    """
    Devuelve los rangos de filas fijos para cada sección según la hoja.

    Returns:
        dict: {
            'activo_corriente': (fila_inicio, fila_fin),
            'activo_no_corriente': (fila_inicio, fila_fin),
            'pasivo_corriente': (fila_inicio, fila_fin),
            'pasivo_no_corriente': (fila_inicio, fila_fin),
            'patrimonio': (fila_inicio, fila_fin)
        }
    """
    sheet_title_upper = sheet_title.upper()

    if "ANÁLISIS VERTICAL" in sheet_title_upper or "ANALISIS VERTICAL" in sheet_title_upper:
        return {
            'activo_corriente': (11, 27),
            'activo_no_corriente': (30, 46),
            'pasivo_corriente': (51, 67),
            'pasivo_no_corriente': (70, 86),
            'patrimonio': (89, 98)
        }
    elif "ESTADOS FINANCIEROS COMPARATIVO" in sheet_title_upper:
        return {
            'activo_corriente': (12, 28),
            'activo_no_corriente': (31, 47),
            'pasivo_corriente': (52, 68),
            'pasivo_no_corriente': (71, 87),
            'patrimonio': (90, 99)
        }
    else:
        # Valores por defecto para otras hojas
        return {
            'activo_corriente': (12, 28),
            'activo_no_corriente': (31, 47),
            'pasivo_corriente': (52, 68),
            'pasivo_no_corriente': (71, 87),
            'patrimonio': (90, 99)
        }


def procesar_hoja_comparativo(sheet, cuentas_clasificadas, año_actual, año_anterior):
    """Procesa la hoja Estados Financieros Comparativo"""
    columnas = encontrar_columnas_años(sheet)
    rangos = obtener_rangos_fijos_por_hoja(sheet.title)

    if not columnas['año_actual'] or not columnas['año_anterior']:
        logger.error("No se encontraron las columnas de años")
        return

    # Insertar cuentas en cada sección usando rangos fijos
    insertar_cuentas_en_rango(sheet, rangos['activo_corriente'],
                              cuentas_clasificadas['Activo']['Corriente'],
                              columnas, año_actual, año_anterior, 'Activo Corriente')

    insertar_cuentas_en_rango(sheet, rangos['activo_no_corriente'],
                              cuentas_clasificadas['Activo']['No Corriente'],
                              columnas, año_actual, año_anterior, 'Activo No Corriente')

    insertar_cuentas_en_rango(sheet, rangos['pasivo_corriente'],
                              cuentas_clasificadas['Pasivo']['Corriente'],
                              columnas, año_actual, año_anterior, 'Pasivo Corriente')

    insertar_cuentas_en_rango(sheet, rangos['pasivo_no_corriente'],
                              cuentas_clasificadas['Pasivo']['No Corriente'],
                              columnas, año_actual, año_anterior, 'Pasivo No Corriente')

    insertar_cuentas_en_rango(sheet, rangos['patrimonio'],
                              cuentas_clasificadas['Patrimonio'],
                              columnas, año_actual, año_anterior, 'Patrimonio')


def procesar_hoja_analisis_vertical(sheet, cuentas_clasificadas, año_actual, año_anterior):
    """Procesa la hoja Análisis Vertical"""
    # Usa la misma lógica que comparativo pero con rangos específicos para análisis vertical
    procesar_hoja_comparativo(
        sheet, cuentas_clasificadas, año_actual, año_anterior)


def insertar_cuentas_en_rango(sheet, rango, datos_seccion, columnas, año_actual, año_anterior, nombre_seccion):
    """
    Inserta las cuentas de una sección en un rango específico de filas.

    Args:
        sheet: Hoja de Excel
        rango: Tupla (fila_inicio, fila_fin) 
        datos_seccion: Datos de la sección
        columnas: Diccionario con columnas de años
        año_actual: Año actual
        año_anterior: Año anterior
        nombre_seccion: Nombre de la sección para logging
    """
    fila_inicio, fila_fin = rango

    # Obtener todas las cuentas únicas
    cuentas_unicas = set()
    if isinstance(datos_seccion, dict) and año_actual in datos_seccion:
        cuentas_unicas.update(datos_seccion[año_actual].keys())
    if isinstance(datos_seccion, dict) and año_anterior in datos_seccion:
        cuentas_unicas.update(datos_seccion[año_anterior].keys())

    cuentas_ordenadas = sorted(list(cuentas_unicas))
    filas_disponibles = fila_fin - fila_inicio + 1

    for i, cuenta in enumerate(cuentas_ordenadas):
        if i >= filas_disponibles:
            logger.error(
                f"No hay más espacio para insertar la cuenta '{cuenta}' en {nombre_seccion}")
            break

        fila_actual = fila_inicio + i

        # Insertar nombre de cuenta en columna C
        sheet.cell(row=fila_actual, column=3).value = cuenta

        # Insertar valor año actual
        if isinstance(datos_seccion, dict) and año_actual in datos_seccion:
            valor_actual = datos_seccion[año_actual].get(cuenta, 0)
            sheet.cell(row=fila_actual,
                       column=columnas['año_actual']).value = valor_actual

        # Insertar valor año anterior
        if isinstance(datos_seccion, dict) and año_anterior in datos_seccion:
            valor_anterior = datos_seccion[año_anterior].get(cuenta, 0)
            sheet.cell(row=fila_actual,
                       column=columnas['año_anterior']).value = valor_anterior
