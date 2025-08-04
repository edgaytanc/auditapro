from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    buscar_fila_por_valor
)

def insertar_datos_estado_resultados(workbook, cuentas_por_fecha, fechas_semestrales):
    """
    Inserta los datos en el archivo CENTRALIZADORA DEL ESTADO DE RESULTADOS
    
    Args:
        workbook: El libro de Excel a procesar
        cuentas_por_fecha: Diccionario con las cuentas por fecha
        fechas_semestrales: Lista con todas las fechas semestrales
    """
    # Obtener la hoja activa
    sheet = workbook.active
    
    # Preparar fechas
    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    if not fechas_excel:
        return
    
    # Insertar fechas en celdas
    insertar_fechas_en_celdas(sheet, fechas_excel)
    
    # Obtener todas las cuentas únicas de todas las fechas
    todas_las_cuentas = set()
    for fecha, cuentas in cuentas_por_fecha.items():
        todas_las_cuentas.update(cuentas.keys())
    
    # Ordenar las cuentas alfabéticamente
    cuentas_ordenadas = sorted(todas_las_cuentas)
    
    # Fila inicial y fila "Suma" original
    fila_inicio = 13
    fila_suma = buscar_fila_por_valor(sheet, 'B', 'Suma') or 19

    # Calcular si necesitamos insertar filas adicionales antes de la fila Suma
    filas_necesarias = len(cuentas_ordenadas)
    filas_disponibles = fila_suma - fila_inicio  # número de filas antes de la suma

    if filas_necesarias > filas_disponibles:
        filas_a_insertar = filas_necesarias - filas_disponibles
        # Insertar filas justo en la posición de la fila Suma
        sheet.insert_rows(fila_suma, filas_a_insertar)
        # Actualizar la referencia de la fila Suma después de moverla hacia abajo
        fila_suma += filas_a_insertar

    # Insertar cuentas
    fila_actual = fila_inicio
    for cuenta in cuentas_ordenadas:
        sheet[f'B{fila_actual}'] = cuenta

        valores = {
            'D': fechas_año_viejo[0],
            'E': fechas_año_viejo[1],
            'F': fechas_año_viejo[2],
            'I': fecha_mas_reciente
        }

        for col, fecha in valores.items():
            if fecha in cuentas_por_fecha and cuenta in cuentas_por_fecha[fecha]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        fila_actual += 1

    # Actualizar fórmulas de la fila Suma para cubrir todas las cuentas
    last_row_cuentas = fila_inicio + len(cuentas_ordenadas) - 1
    for col in ['D', 'E', 'F', 'G', 'H', 'I']:
        sheet[f"{col}{fila_suma}"] = f"=SUM({col}{fila_inicio}:{col}{last_row_cuentas})"
