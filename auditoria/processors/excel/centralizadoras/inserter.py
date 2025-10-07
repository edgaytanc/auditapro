from .fechas import preparar_fechas_excel, insertar_fechas_en_celdas
from .utils import mover_imagenes_por_insercion, buscar_fila_por_valor

def procesar_seccion_centralizadora(
    sheet,
    cuentas_por_fecha,
    fechas_columnas,
    ajustes_reclasificaciones,
    secciones,
    fila_inicio,
    texto_suma,
    columnas_suma
):
    """
    Función genérica para procesar una sección de una hoja centralizadora.
    """
    # 1. Obtener cuentas únicas para las secciones dadas
    cuentas_unicas = set()
    for fecha, data in cuentas_por_fecha.items():
        for seccion in secciones:
            # Manejar estructura de datos anidada y plana
            cuentas_seccion = data.get(seccion, data if not isinstance(list(data.values())[0], dict) else {})
            cuentas_unicas.update(cuentas_seccion.keys())
    
    cuentas_ordenadas = sorted(list(cuentas_unicas))

    # 2. Asegurar espacio en la hoja, insertando filas si es necesario
    suma_row = buscar_fila_por_valor(sheet, 'B', texto_suma)
    if not suma_row:
        suma_row = fila_inicio + len(cuentas_ordenadas) + 1 # Fallback si no se encuentra

    filas_disponibles = max(0, suma_row - fila_inicio)
    filas_necesarias = len(cuentas_ordenadas)
    filas_a_insertar = max(0, filas_necesarias - filas_disponibles)

    if filas_a_insertar > 0:
        sheet.insert_rows(suma_row, filas_a_insertar)
        mover_imagenes_por_insercion(sheet, suma_row, filas_a_insertar)
        suma_row += filas_a_insertar

    # 3. Insertar datos en cada fila
    for i, cuenta in enumerate(cuentas_ordenadas):
        fila_actual = fila_inicio + i
        sheet[f'B{fila_actual}'] = cuenta

        # Insertar saldos por fecha
        for col, fecha in fechas_columnas.items():
            valor = 0
            if fecha in cuentas_por_fecha:
                for seccion in secciones:
                    # Adaptarse a la estructura de cuentas_por_fecha
                    if seccion in cuentas_por_fecha[fecha]:
                        valor = cuentas_por_fecha[fecha][seccion].get(cuenta, 0)
                        if valor != 0: break
                    elif not isinstance(list(cuentas_por_fecha[fecha].values())[0], dict):
                        valor = cuentas_por_fecha[fecha].get(cuenta, 0)
                        if valor != 0: break
            sheet[f'{col}{fila_actual}'] = valor

        # Insertar ajustes
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # 4. Actualizar la fila de suma
    if cuentas_ordenadas:
        last_row = fila_inicio + len(cuentas_ordenadas) - 1
        for col in columnas_suma:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"
            
    return filas_a_insertar
