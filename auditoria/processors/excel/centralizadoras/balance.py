from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    procesar_seccion_balance,
    buscar_fila_por_valor
)

def insertar_datos_balance(workbook, cuentas_por_fecha, fechas_semestrales):
    """
    Inserta los datos en el archivo CENTRALIZADORA BALANCE
    
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
    
    # ------------------------------------------------------------------
    # 1. Procesar ACTIVO (filas 13-19)
    # ------------------------------------------------------------------
    # Primero obtener la lista de cuentas de activo para calcular desplazamiento
    activo_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                            if "Activo" in secciones for cuenta in secciones["Activo"].keys()})
    
    # Calcular cuántas filas se necesitarán insertar
    filas_activo_necesarias = len(activo_cuentas) if activo_cuentas else 0
    filas_activo_originales = 7  # filas 13-19 = 7 filas
    filas_insertadas_activo = max(0, filas_activo_necesarias - filas_activo_originales)
    
    procesar_seccion_balance(sheet, cuentas_por_fecha, fechas_año_viejo, fecha_mas_reciente, 
                             "Activo", 13, 19)
    
    # Ajustar fila "Suma Activo" según la cantidad real de cuentas de activo
    if activo_cuentas:
        last_row_activo = 13 + len(activo_cuentas) - 1
        suma_activo_row = buscar_fila_por_valor(sheet, 'B', 'Suma Activo')
        
        # Reubicar la fila de suma si quedó separada
        if suma_activo_row and suma_activo_row != last_row_activo + 1:
            filas_a_subir = suma_activo_row - (last_row_activo + 1)
            if filas_a_subir > 0:
                sheet.move_range(f"A{suma_activo_row}:I{suma_activo_row}", rows=-filas_a_subir)
                suma_activo_row -= filas_a_subir
        
        # Actualizar fórmulas de suma para cubrir todo el rango real de activo
        if suma_activo_row:
            for col in ['D', 'E', 'F', 'G', 'H', 'I']:
                sheet[f"{col}{suma_activo_row}"] = f"=SUBTOTAL(9,{col}13:{col}{last_row_activo})"
    
    # ------------------------------------------------------------------
    # 2. Procesar PASIVO Y PATRIMONIO combinados (posición dinámica)
    # ------------------------------------------------------------------
    # Calcular nueva posición de inicio considerando las filas insertadas en activo
    nueva_fila_inicio_pp = 22 + filas_insertadas_activo
    nueva_fila_fin_pp = 24 + filas_insertadas_activo  # rango fila 22-24
    
    # Construir listas ordenadas de cuentas (Pasivo primero, luego Patrimonio)
    pasivo_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                            if "Pasivo" in secciones for cuenta in secciones["Pasivo"].keys()})
    patrimonio_cuentas = sorted({cuenta for fecha, secciones in cuentas_por_fecha.items() 
                                if "Patrimonio" in secciones for cuenta in secciones["Patrimonio"].keys()})
    todas_pp_cuentas = pasivo_cuentas + patrimonio_cuentas
    
    if todas_pp_cuentas:
        # Reorganizar el diccionario para procesar_seccion_balance con clave ficticia 'PP'
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
        
        # Insertar todas las cuentas contiguamente desde la nueva posición
        procesar_seccion_balance(
            sheet,
            cuentas_pp_por_fecha,
            fechas_año_viejo,
            fecha_mas_reciente,
            "PP",
            nueva_fila_inicio_pp,
            nueva_fila_fin_pp,
            orden_explicit=todas_pp_cuentas,
        )
        
        # Ajustar fila "Suma Pasivo y Patrimonio" según la cantidad real de cuentas
        last_row_pp = nueva_fila_inicio_pp + len(todas_pp_cuentas) - 1
        suma_pp_row = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio')
        
        # Reubicar la fila de suma si quedó separada
        if suma_pp_row and suma_pp_row != last_row_pp + 1:
            filas_a_subir = suma_pp_row - (last_row_pp + 1)
            if filas_a_subir > 0:
                sheet.move_range(f"A{suma_pp_row}:I{suma_pp_row}", rows=-filas_a_subir)
                suma_pp_row -= filas_a_subir
        
        # Actualizar fórmulas de suma para cubrir todo el rango real de pasivo y patrimonio
        if suma_pp_row:
            for col in ['D', 'E', 'F', 'G', 'H', 'I']:
                sheet[f"{col}{suma_pp_row}"] = f"=SUM({col}{nueva_fila_inicio_pp}:{col}{last_row_pp})"