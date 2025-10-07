import logging

logger = logging.getLogger(__name__)

def insertar_cuentas_en_rango(sheet, rango, datos_seccion, columnas, año_actual, año_anterior, nombre_seccion):
    """
    Inserta las cuentas de una sección en un rango específico de filas.
    """
    fila_inicio, fila_fin = rango
    filas_disponibles = fila_fin - fila_inicio + 1

    # Obtener todas las cuentas únicas de la sección para ambos años
    cuentas_unicas = set()
    if isinstance(datos_seccion, dict):
        if año_actual in datos_seccion:
            cuentas_unicas.update(datos_seccion[año_actual].keys())
        if año_anterior in datos_seccion:
            cuentas_unicas.update(datos_seccion[año_anterior].keys())
    
    cuentas_ordenadas = sorted(list(cuentas_unicas))

    for i, cuenta in enumerate(cuentas_ordenadas):
        if i >= filas_disponibles:
            logger.warning(f"No hay más espacio para insertar la cuenta '{cuenta}' en la sección '{nombre_seccion}'. Se omitirán las cuentas restantes.")
            break

        fila_actual = fila_inicio + i

        # Insertar nombre de cuenta en columna C (columna 3)
        sheet.cell(row=fila_actual, column=3).value = cuenta

        # Insertar valores para año actual y anterior
        if isinstance(datos_seccion, dict):
            if año_actual in datos_seccion:
                valor_actual = datos_seccion[año_actual].get(cuenta, 0)
                sheet.cell(row=fila_actual, column=columnas['año_actual']).value = valor_actual
            
            if año_anterior in datos_seccion:
                valor_anterior = datos_seccion[año_anterior].get(cuenta, 0)
                sheet.cell(row=fila_actual, column=columnas['año_anterior']).value = valor_anterior
