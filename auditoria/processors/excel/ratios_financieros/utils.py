def encontrar_columnas_años(sheet):
    """Encuentra las columnas donde están 'Año actual' y 'Año anterior' en las primeras 10 filas."""
    columnas = {'año_actual': None, 'año_anterior': None}
    for fila in range(1, 11):
        for col in range(1, 15):
            celda = sheet.cell(row=fila, column=col)
            if isinstance(celda.value, str):
                valor = celda.value.strip().lower()
                if 'año actual' in valor:
                    columnas['año_actual'] = col
                elif 'año anterior' in valor:
                    columnas['año_anterior'] = col
    return columnas

def obtener_rangos_fijos_por_hoja(sheet_title):
    """
    Devuelve los rangos de filas fijos para cada sección según el título de la hoja.
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
    # Por defecto, se usan los rangos para "ESTADOS FINANCIEROS COMPARATIVO"
    return {
        'activo_corriente': (12, 28),
        'activo_no_corriente': (31, 47),
        'pasivo_corriente': (52, 68),
        'pasivo_no_corriente': (71, 87),
        'patrimonio': (90, 99)
    }
