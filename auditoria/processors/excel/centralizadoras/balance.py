from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    buscar_fila_por_valor
)

def insertar_datos_balance(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    """
    Inserta datos en CENTRALIZADORA BALANCE con ajustes.
    
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

    # ------------------------------------------------------------------
    # 2. Procesar ACTIVO (filas 13-19)
    # ------------------------------------------------------------------
    # Obtener cuentas de activo
    activo_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                           if "Activo" in secciones for cuenta in secciones["Activo"].keys()})
    
    # Insertar datos de activo
    fila_inicio_activo = 13
    for i, cuenta in enumerate(activo_cuentas):
        fila_actual = fila_inicio_activo + i
        
        # Nombre de la cuenta (columna B)
        sheet[f'B{fila_actual}'] = cuenta

        # Insertar saldos por fecha (columnas D, E, F, I)
        fechas_columnas = {
            'D': fechas_año_viejo[0],  # 01/01/2023
            'E': fechas_año_viejo[1],  # 31/07/2023
            'F': fechas_año_viejo[2],  # 31/12/2023
            'I': fecha_mas_reciente    # 31/12/2024
        }
        
        for col, fecha in fechas_columnas.items():
            if fecha in cuentas_por_fecha and "Activo" in cuentas_por_fecha[fecha] and cuenta in cuentas_por_fecha[fecha]["Activo"]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha]["Activo"][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        # Insertar ajustes (columnas G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # Ajustar fila "Suma Activo"
    if activo_cuentas:
        last_row_activo = fila_inicio_activo + len(activo_cuentas) - 1
        suma_activo_row = buscar_fila_por_valor(sheet, 'B', 'Suma Activo') or (last_row_activo + 1)
        
        if suma_activo_row != last_row_activo + 1:
            sheet.move_range(f"A{suma_activo_row}:I{suma_activo_row}", rows=-(suma_activo_row - (last_row_activo + 1)))
            suma_activo_row = last_row_activo + 1
        
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_activo_row}"] = f"=SUM({col}{fila_inicio_activo}:{col}{last_row_activo})"

    # ------------------------------------------------------------------
    # 3. Procesar PASIVO Y PATRIMONIO (posición dinámica)
    # ------------------------------------------------------------------
    # Calcular nueva posición de inicio (22 + filas insertadas en activo)
    filas_insertadas_activo = max(0, len(activo_cuentas) - 7)  # 7 filas originales (13-19)
    fila_inicio_pp = 22 + filas_insertadas_activo

    # Obtener cuentas de pasivo y patrimonio
    pasivo_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                            if "Pasivo" in secciones for cuenta in secciones["Pasivo"].keys()})
    patrimonio_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                                if "Patrimonio" in secciones for cuenta in secciones["Patrimonio"].keys()})
    todas_pp_cuentas = pasivo_cuentas + patrimonio_cuentas

    # Insertar datos de pasivo y patrimonio
    for i, cuenta in enumerate(todas_pp_cuentas):
        fila_actual = fila_inicio_pp + i
        
        # Nombre de la cuenta (columna B)
        sheet[f'B{fila_actual}'] = cuenta

        # Determinar sección (Pasivo o Patrimonio)
        seccion = "Pasivo" if cuenta in pasivo_cuentas else "Patrimonio"

        # Insertar saldos por fecha (columnas D, E, F, I)
        for col, fecha in fechas_columnas.items():
            if fecha in cuentas_por_fecha and seccion in cuentas_por_fecha[fecha] and cuenta in cuentas_por_fecha[fecha][seccion]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][seccion][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        # Insertar ajustes (columnas G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # Ajustar fila "Suma Pasivo y Patrimonio"
    if todas_pp_cuentas:
        last_row_pp = fila_inicio_pp + len(todas_pp_cuentas) - 1
        suma_pp_row = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio') or (last_row_pp + 1)
        
        if suma_pp_row != last_row_pp + 1:
            sheet.move_range(f"A{suma_pp_row}:I{suma_pp_row}", rows=-(suma_pp_row - (last_row_pp + 1)))
            suma_pp_row = last_row_pp + 1
        
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_pp_row}"] = f"=SUM({col}{fila_inicio_pp}:{col}{last_row_pp})"