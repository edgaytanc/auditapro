from datetime import datetime

def process_comparative_file(workbook, balances, registros_auxiliares):
    """Procesa el archivo comparativo entre estados financieros y registros auxiliares."""
    if not workbook.worksheets: return workbook
    
    sheet = workbook.worksheets[0]
    fila_inicio, col_cuenta, col_balance, col_auxiliar = 41, 2, 3, 4
    max_filas = fila_inicio + 29
    
    # Obtener año más reciente y clasificar cuentas
    año_actual = obtener_año_mas_reciente(balances)
    if not año_actual: return workbook
    
    # Clasificar cuentas por categoría
    cuentas_por_categoria = {'Activo': {}, 'Pasivo': {}, 'Patrimonio': {}, 'ESTADO DE RESULTADOS': {}}
    for clave, valor in balances.items():
        if año_actual in clave and len(partes := clave.split('-')) >= 6:
            categoria, cuenta = partes[4], partes[5]
            if categoria in cuentas_por_categoria:
                cuentas_por_categoria[categoria][cuenta] = valor
    
    # Procesar cuentas en orden específico
    fila_actual, cuentas_procesadas = fila_inicio, set()
    for categoria in ['Activo', 'Pasivo', 'Patrimonio', 'ESTADO DE RESULTADOS']:
        cuentas = cuentas_por_categoria.get(categoria, {})
        
        # Primero cuentas comunes
        for cuenta, valor_balance in cuentas.items():
            if cuenta in registros_auxiliares and cuenta not in cuentas_procesadas:
                sheet.cell(row=fila_actual, column=col_cuenta).value = cuenta
                sheet.cell(row=fila_actual, column=col_balance).value = valor_balance
                sheet.cell(row=fila_actual, column=col_auxiliar).value = registros_auxiliares[cuenta]
                cuentas_procesadas.add(cuenta)
                if (fila_actual := fila_actual + 1) > max_filas: return workbook
        
        # Luego cuentas solo en balances
        for cuenta, valor_balance in cuentas.items():
            if cuenta not in cuentas_procesadas:
                sheet.cell(row=fila_actual, column=col_cuenta).value = cuenta
                sheet.cell(row=fila_actual, column=col_balance).value = valor_balance
                sheet.cell(row=fila_actual, column=col_auxiliar).value = 0
                cuentas_procesadas.add(cuenta)
                if (fila_actual := fila_actual + 1) > max_filas: return workbook
    
    # Finalmente cuentas solo en auxiliares
    for cuenta, valor_auxiliar in registros_auxiliares.items():
        if cuenta not in cuentas_procesadas:
            sheet.cell(row=fila_actual, column=col_cuenta).value = cuenta
            sheet.cell(row=fila_actual, column=col_balance).value = 0
            sheet.cell(row=fila_actual, column=col_auxiliar).value = valor_auxiliar
            if (fila_actual := fila_actual + 1) > max_filas: break
    
    return workbook

def obtener_año_mas_reciente(balances):
    """Obtiene el año más reciente de los balances."""
    años = {}
    
    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 4:
            tipo, fecha = partes[0], f"{partes[1]}-{partes[2]}-{partes[3]}"
            try:
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
                año = fecha_obj.year
                if año not in años or fecha_obj > años[año]['fecha']:
                    años[año] = {'fecha': fecha_obj, 'tipo': tipo, 'fecha_str': fecha}
            except ValueError:
                continue
    
    return f"{años[año_mas_reciente]['tipo']}-{años[año_mas_reciente]['fecha_str']}" if (años and (año_mas_reciente := max(años.keys()))) else None