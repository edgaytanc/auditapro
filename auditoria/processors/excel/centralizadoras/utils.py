from openpyxl.utils.cell import coordinate_from_string

def mover_imagenes_por_insercion(sheet, start_row: int, delta_rows: int):
    """Mueve imágenes ancladas en filas >= start_row hacia abajo delta_rows."""
    if not hasattr(sheet, "_images") or delta_rows == 0:
        return

    for img in list(sheet._images):
        try:
            anchor = img.anchor
            if isinstance(anchor, str):
                col_letters, row = coordinate_from_string(anchor)
                if row >= start_row:
                    img.anchor = f"{col_letters}{row + delta_rows}"
                continue
            if hasattr(anchor, "_from"):
                if anchor._from.row + 1 >= start_row:
                    anchor._from.row += delta_rows
                if hasattr(anchor, "_to") and anchor._to is not None and anchor._to.row + 1 >= start_row:
                    anchor._to.row += delta_rows
        except Exception:
            continue

def buscar_fila_por_valor(sheet, col_letter: str, texto: str):
    """Devuelve el número de fila donde la celda de la columna col_letter contiene 'texto'."""
    texto_lower = texto.lower()
    for row in range(1, sheet.max_row + 1):
        val = sheet[f"{col_letter}{row}"].value
        if isinstance(val, str) and texto_lower in val.lower():
            return row
    return None
