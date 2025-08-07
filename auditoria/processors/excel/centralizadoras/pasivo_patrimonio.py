from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    buscar_fila_por_valor
)

def insertar_datos_pasivo_patrimonio(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    """
    Inserta datos en CENTRALIZADORA PASIVO-PATRIMONIO con ajustes.
    
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

    # 2. Obtener cuentas únicas de Pasivo y Patrimonio
    pasivo_cuentas = set()
    patrimonio_cuentas = set()
    
    for fecha, secciones in cuentas_por_fecha.items():
        if "Pasivo" in secciones:
            for cuenta in secciones["Pasivo"].keys():
                pasivo_cuentas.add(cuenta)
        if "Patrimonio" in secciones:
            for cuenta in secciones["Patrimonio"].keys():
                patrimonio_cuentas.add(cuenta)
    
    todas_cuentas = sorted(pasivo_cuentas) + sorted(patrimonio_cuentas)

    # 3. Insertar datos por fila (fila_inicio = 13)
    fila_inicio = 13
    for i, cuenta in enumerate(todas_cuentas):
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
            seccion = "Pasivo" if cuenta in pasivo_cuentas else "Patrimonio"
            
            if fecha in cuentas_por_fecha and seccion in cuentas_por_fecha[fecha] and cuenta in cuentas_por_fecha[fecha][seccion]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][seccion][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        # Insertar ajustes (columnas G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # 4. Actualizar fila de suma
    if todas_cuentas:
        last_row = fila_inicio + len(todas_cuentas) - 1
        suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio') or (last_row + 1)
        
        # Mover fila de suma si es necesario
        if suma_row != last_row + 1:
            sheet.move_range(f"A{suma_row}:I{suma_row}", rows=-(suma_row - (last_row + 1)))
            suma_row = last_row + 1
        
        # Actualizar fórmulas de suma (columnas D-I)
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"