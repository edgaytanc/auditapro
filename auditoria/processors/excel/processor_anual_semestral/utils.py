from copy import copy

def formatear_fecha(fecha_str):
    """Formatea una fecha en formato YYYY-MM-DD a 'Al DD/MM/YYYY'"""
    try:
        partes = fecha_str.split('-')
        return f"Al {partes[2]}/{partes[1]}/{partes[0]}" if len(partes) >= 3 else fecha_str
    except Exception:
        return fecha_str

def copiar_estilo_fila(sheet, fila_origen, fila_destino, columnas=None):
    """Copia el estilo completo de una fila a otra."""
    if columnas is None:
        columnas = range(1, sheet.max_column + 1)
    for col in columnas:
        celda_origen = sheet.cell(row=fila_origen, column=col)
        celda_destino = sheet.cell(row=fila_destino, column=col)
        if celda_origen.has_style:
            for attr in ['border', 'font', 'fill', 'alignment']:
                setattr(celda_destino, attr, copy(getattr(celda_origen, attr)))
            celda_destino.number_format = celda_origen.number_format

def buscar_filas_clave(sheet):
    """Busca las filas clave (TOTAL ACTIVO, etc.) en la hoja Excel."""
    filas = {'BALANCE GENERAL': None, 'TOTAL ACTIVO': None, 'TOTAL PASIVO Y PATRIMONIO': None}
    for i in range(1, sheet.max_row + 1):
        for col in [2, 1]: # Prioriza columna B
            valor_celda = str(sheet.cell(row=i, column=col).value).upper() if sheet.cell(row=i, column=col).value else ""
            for clave in filas:
                if filas[clave] is None and clave in valor_celda:
                    filas[clave] = i
    return {
        'BALANCE GENERAL': filas.get('BALANCE GENERAL') or 14,
        'TOTAL ACTIVO': filas.get('TOTAL ACTIVO') or 22,
        'TOTAL PASIVO Y PATRIMONIO': filas.get('TOTAL PASIVO Y PATRIMONIO') or 26
    }

def encontrar_fila_cuenta_normal(sheet, fila_inicio, fila_fin):
    """Encuentra una fila de cuenta normal para usar como referencia de estilo."""
    for i in range(fila_inicio, fila_fin):
        valor_celda = str(sheet.cell(row=i, column=2).value).upper() if sheet.cell(row=i, column=2).value else ""
        if valor_celda and "TOTAL" not in valor_celda:
            return i
    return None

def _columnas_valores(tipo_balance: str, fechas: list):
    """Devuelve la lista de índices de columnas que contienen valores."""
    return list(range(3, 3 + (min(2, len(fechas)) if tipo_balance == "ANUAL" else len(fechas))))

def _actualizar_formula_suma(sheet, fila_suma: int, columnas: list[int], fila_inicio: int, fila_fin: int):
    """Reescribe la fórmula de suma en la fila dada para las columnas indicadas."""
    if fila_fin >= fila_inicio:
        for col in columnas:
            celda_inicio = sheet.cell(row=fila_inicio, column=col).coordinate
            celda_fin = sheet.cell(row=fila_fin, column=col).coordinate
            sheet.cell(row=fila_suma, column=col).value = f"=SUM({celda_inicio}:{celda_fin})"
