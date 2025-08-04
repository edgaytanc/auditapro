from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    procesar_seccion_balance,
    buscar_fila_por_valor
)

def insertar_datos_activo(workbook, cuentas_por_fecha, fechas_semestrales):
    """
    Inserta los datos en el archivo CENTRALIZADORA DEL ACTIVO
    
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
    
    # Crear un diccionario adaptado para procesar_seccion_balance
    cuentas_adaptadas = {}
    for fecha, cuentas in cuentas_por_fecha.items():
        cuentas_adaptadas[fecha] = {'Activo': cuentas}
    
    procesar_seccion_balance(sheet, cuentas_adaptadas, fechas_año_viejo, fecha_mas_reciente, 
                             "Activo", 13, 19)
    
    # ------------------------------------------------------------------
    # Ajustar fila "Suma Activo" según la cantidad real de cuentas
    # ------------------------------------------------------------------
    todas_las_cuentas = sorted({cuenta for cuentas in cuentas_por_fecha.values() for cuenta in cuentas.keys()})
    
    if todas_las_cuentas:
        last_row_cuentas = 13 + len(todas_las_cuentas) - 1
        
        suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma Activo')
        
        # Reubicar la fila de suma si quedó separada
        if suma_row and suma_row != last_row_cuentas + 1:
            filas_a_subir = suma_row - (last_row_cuentas + 1)
            if filas_a_subir > 0:
                sheet.move_range(f"A{suma_row}:I{suma_row}", rows=-filas_a_subir)
                suma_row -= filas_a_subir
        
        # Actualizar fórmulas de suma para cubrir todo el rango real
        if suma_row:
            for col in ['D', 'E', 'F', 'G', 'H', 'I']:
                sheet[f"{col}{suma_row}"] = f"=SUM({col}13:{col}{last_row_cuentas})"