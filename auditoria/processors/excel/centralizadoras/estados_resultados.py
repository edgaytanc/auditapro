from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    buscar_fila_por_valor
)

def insertar_datos_estado_resultados(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    """
    Inserta datos en CENTRALIZADORA ESTADO DE RESULTADOS con ajustes.
    
    Estructura de columnas (según imagen):
    - D: Al 01/01/2023
    - E: Al 31/07/2023
    - F: Al 31/12/2023
    - G: Debe
    - H: Haber
    - I: Al 31/12/2024
    """
    sheet = workbook.active

    # 1. Preparar fechas
    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    insertar_fechas_en_celdas(sheet, fechas_excel)

    # 2. Obtener cuentas únicas
    todas_cuentas = set()
    for fecha, cuentas in cuentas_por_fecha.items():
        for cuenta in cuentas.keys():
            todas_cuentas.add(cuenta)
    
    cuentas_ordenadas = sorted(todas_cuentas)

    # 3. Insertar datos por fila (fila_inicio = 13)
    fila_inicio = 13
    for i, cuenta in enumerate(cuentas_ordenadas):
        fila_actual = fila_inicio + i
        
        # Nombre de la cuenta (columna B)
        sheet[f'B{fila_actual}'] = cuenta

        # Insertar saldos por fecha (columnas D, E, F, I)
        fechas_columnas = {
            'D': fechas_año_viejo[0],  # 01/01/2023
            'E': fechas_año_viejo[1],  # 31/07/2023
            'F': fechas_año_viejo[2],  # 31/12/2023
            'I': fecha_mas_reciente   # 31/12/2024
        }
        
        for col, fecha in fechas_columnas.items():
            if fecha in cuentas_por_fecha and cuenta in cuentas_por_fecha[fecha]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        # Insertar ajustes (columnas G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # 4. Actualizar fila de suma
    if cuentas_ordenadas:
        last_row = fila_inicio + len(cuentas_ordenadas) - 1
        suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma') or (last_row + 1)
        
        # Mover fila de suma si es necesario
        if suma_row != last_row + 1:
            sheet.move_range(f"A{suma_row}:I{suma_row}", rows=-(suma_row - (last_row + 1)))
            suma_row = last_row + 1
        
        # Actualizar fórmulas de suma (columnas D-I)
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"