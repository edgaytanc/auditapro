from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    procesar_seccion_balance,
    buscar_fila_por_valor
)

def insertar_datos_activo(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    sheet = workbook.active
    
    # 1. Preparar fechas
    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    insertar_fechas_en_celdas(sheet, fechas_excel)
    
    # 2. Procesar cada cuenta
    fila_inicio = 13  # Fila donde comienzan las cuentas de activo
    todas_cuentas = set()
    
    # Obtener todas las cuentas únicas (ya no necesitamos quitar el sufijo -NT)
    for fecha, cuentas in cuentas_por_fecha.items():
        for cuenta in cuentas.keys():
            todas_cuentas.add(cuenta)

    # Asegurar espacio: insertar filas antes de la fila "Suma Activo" si faltan
    suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma Activo')
    if not suma_row:
        suma_row = fila_inicio + 1
    filas_disponibles = max(0, suma_row - fila_inicio)
    filas_necesarias = len(todas_cuentas)
    filas_a_insertar = max(0, filas_necesarias - filas_disponibles)
    if filas_a_insertar:
        sheet.insert_rows(suma_row, filas_a_insertar)
        suma_row += filas_a_insertar

    # Mapear fechas a columnas una sola vez
    fechas_columnas = {
        'D': fechas_año_viejo[0],  # 01/01/xxxx
        'E': fechas_año_viejo[1],  # 31/07/xxxx
        'F': fechas_año_viejo[2],  # 31/12/xxxx
        'I': fecha_mas_reciente    # 31/12/xxxx
    }
    
    # Insertar datos en cada fila
    for i, cuenta in enumerate(sorted(todas_cuentas)):
        fila_actual = fila_inicio + i
        
        # Nombre de la cuenta (columna B)
        sheet[f'B{fila_actual}'] = cuenta
        
        # Insertar saldos por fecha (columnas D, E, F, I)
        for col, fecha in fechas_columnas.items():
            if fecha in cuentas_por_fecha and cuenta in cuentas_por_fecha[fecha]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0
        
        # Insertar ajustes (columna G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)
    
    # 3. Actualizar fila de suma (columnas D-I) sin moverla
    if todas_cuentas:
        last_row = fila_inicio + len(todas_cuentas) - 1
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"