from copy import copy

def copiar_estilo(celda_origen, celda_destino):
    """Copia el estilo completo de una celda a otra."""
    if celda_origen and celda_destino:
        if celda_origen.has_style:
            celda_destino.font = copy(celda_origen.font)
            celda_destino.border = copy(celda_origen.border)
            celda_destino.fill = copy(celda_origen.fill)
            celda_destino.alignment = copy(celda_origen.alignment)
            celda_destino.number_format = celda_origen.number_format

def actualizar_formulas_fila(sheet, fila, fila_inicio, fila_fin, columnas_a_actualizar):
    """Actualiza las fórmulas de suma para un rango de columnas en una fila específica."""
    for col in columnas_a_actualizar:
        celda = sheet.cell(row=fila, column=col)
        if celda.data_type == 'f':
            nueva_formula = f"=SUM({sheet.cell(row=fila_inicio, column=col).coordinate}:{sheet.cell(row=fila_fin, column=col).coordinate})"
            celda.value = nueva_formula
