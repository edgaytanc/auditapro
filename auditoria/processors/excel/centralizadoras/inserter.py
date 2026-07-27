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
    # Import diferido para evitar ciclos de importación con los servicios
    from auditoria.services.referencias import ref_para_cuenta

    # 1. Obtener cuentas únicas para las secciones dadas, recordando la
    #    sección de origen de cada cuenta (la sección manda sobre las palabras
    #    clave al asignar la referencia de sumaria: p. ej. 'Resultado del
    #    ejercicio' en Patrimonio referencia J-1, no R-1).
    cuentas_unicas = set()
    seccion_por_cuenta = {}
    for fecha, data in cuentas_por_fecha.items():
        for seccion in secciones:
            # Manejar estructura de datos anidada y plana
            cuentas_seccion = data.get(seccion, data if not isinstance(list(data.values())[0], dict) else {})
            cuentas_unicas.update(cuentas_seccion.keys())
            if isinstance(data.get(seccion), dict):
                for cuenta in cuentas_seccion:
                    seccion_por_cuenta.setdefault(cuenta, seccion)
            else:
                # Estructura plana: todas las cuentas pertenecen a la única sección
                for cuenta in cuentas_seccion:
                    seccion_por_cuenta.setdefault(cuenta, secciones[0])

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

        # Ref P/T (columna C): referencia de la cédula sumaria asociada.
        # Nunca dejar el valor de muestra de la plantilla en filas escritas.
        ref = ref_para_cuenta(cuenta, seccion=seccion_por_cuenta.get(cuenta))
        sheet[f'C{fila_actual}'] = ref if ref else ''

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

    # 4. Vaciar las filas de muestra que trae la plantilla y no se usaron.
    #    Las centralizadoras oficiales vienen precargadas con cuentas de ejemplo
    #    ('Bancos', 'Inventarios'…) y sus propias Ref P/T (A-2, A-3…). Si no se
    #    limpian, el papel descargado mezcla las cuentas reales del Excel con
    #    esas de muestra y sus referencias equivocadas.
    primera_libre = fila_inicio + len(cuentas_ordenadas)
    for fila in range(primera_libre, suma_row):
        for col in ('B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'):
            sheet[f'{col}{fila}'] = None

    # 5. Actualizar la fila de suma
    if cuentas_ordenadas:
        last_row = fila_inicio + len(cuentas_ordenadas) - 1
        for col in columnas_suma:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"

    return filas_a_insertar
