from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    procesar_seccion_balance,
    buscar_fila_por_valor
)

def insertar_datos_pasivo_patrimonio(workbook, cuentas_por_fecha, fechas_semestrales):
    """
    Inserta los datos en el archivo CENTRALIZADORA DEL PASIVO Y PATRIMONIO
    
    Procesa dos secciones (Pasivo y Patrimonio) en la misma hoja.
    """
    sheet = workbook.active

    # Preparar fechas
    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    if not fechas_excel:
        return

    # Insertar fechas en celdas
    insertar_fechas_en_celdas(sheet, fechas_excel)

    # ------------------------------------------------------------------
    # 1. Construir listas ordenadas de cuentas (Pasivo primero, luego Patrimonio)
    # ------------------------------------------------------------------
    pasivo_cuentas = sorted({cuenta for data in cuentas_por_fecha.values() if "Pasivo" in data for cuenta in data["Pasivo"].keys()})
    patrimonio_cuentas = sorted({cuenta for data in cuentas_por_fecha.values() if "Patrimonio" in data for cuenta in data["Patrimonio"].keys()})
    todas_las_cuentas = pasivo_cuentas + patrimonio_cuentas

    if not todas_las_cuentas:
        return

    # ------------------------------------------------------------------
    # 2. Reorganizar el diccionario para procesar_seccion_balance con clave ficticia 'PP'
    # ------------------------------------------------------------------
    cuentas_pp_por_fecha = {}
    for fecha, secciones in cuentas_por_fecha.items():
        combinado = {}
        # Pasivo primero
        for c in pasivo_cuentas:
            if "Pasivo" in secciones and c in secciones["Pasivo"]:
                combinado[c] = secciones["Pasivo"][c]
        # Patrimonio después
        for c in patrimonio_cuentas:
            if "Patrimonio" in secciones and c in secciones["Patrimonio"]:
                combinado[c] = secciones["Patrimonio"][c]
        cuentas_pp_por_fecha[fecha] = {"PP": combinado}

    # ------------------------------------------------------------------
    # 3. Insertar todas las cuentas contiguamente a partir de la fila 13
    # ------------------------------------------------------------------
    procesar_seccion_balance(
        sheet,
        cuentas_pp_por_fecha,
        fechas_año_viejo,
        fecha_mas_reciente,
        "PP",
        13,
        19,
        orden_explicit=todas_las_cuentas,
    )

    # ------------------------------------------------------------------
    # 4. Reubicar la fila "Suma Pasivo y Patrimonio" inmediatamente después de la última cuenta
    # ------------------------------------------------------------------
    last_row_cuentas = 13 + len(todas_las_cuentas) - 1
    suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio')
    if suma_row and suma_row != last_row_cuentas + 1:
        filas_a_subir = suma_row - (last_row_cuentas + 1)
        if filas_a_subir > 0:
            sheet.move_range(f"A{suma_row}:I{suma_row}", rows=-filas_a_subir)
            suma_row = suma_row - filas_a_subir

    # ------------------------------------------------------------------
    # 5. Actualizar las fórmulas de la fila de suma según el nuevo rango
    # ------------------------------------------------------------------
    if suma_row:
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}13:{col}{last_row_cuentas})"

    return  # Fin de insertar_datos_pasivo_patrimonio