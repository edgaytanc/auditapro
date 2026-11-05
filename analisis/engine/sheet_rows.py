"""Insertar filas en una hoja de Excel como lo hace Excel: todo lo que está debajo baja con sus referencias.

``openpyxl.insert_rows`` solo mueve las celdas; aquí también se ajustan las fórmulas (de todas las hojas),
las celdas combinadas, los altos de fila, el formato condicional, las validaciones, el área de impresión,
los nombres definidos, los saltos de página, el autofiltro y las imágenes.

Regla (la de Excel): una referencia a una fila ``>= idx`` baja ``n`` filas. Un rango que empieza antes de
``idx`` y termina en ``idx`` o después se agranda; por eso se inserta antes de la última fila de detalle y
el ``=SUM(F19:F28)`` del total pasa solo a ``=SUM(F19:F528)``.
"""
from __future__ import annotations

import re
from copy import copy

from openpyxl.cell.cell import MergedCell
from openpyxl.formula.tokenizer import Token, Tokenizer
from openpyxl.formula.translate import Translator
from openpyxl.worksheet.cell_range import CellRange
from openpyxl.worksheet.formula import ArrayFormula

_RX_PART = re.compile(r"^(\$?)([A-Za-z]{1,3})?(\$?)(\d+)?$")
_RX_SHEET = re.compile(r"^(?:(?P<sheet>'(?:[^']|'')+'|[^'!]+)!)?(?P<ref>[^!]+)$")


class ShiftError(Exception):
    """La hoja tiene algo que no se puede desplazar con seguridad (se deja sin insertar filas)."""


def _unquote(name: str) -> str:
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def _shift_part(part: str, idx: int, n: int) -> str:
    m = _RX_PART.match(part)
    if not m or m.group(4) is None:
        return part  # columna completa (A:A) o nombre: no cambia
    row = int(m.group(4))
    if row >= idx:
        row += n
    return f"{m.group(1)}{m.group(2) or ''}{m.group(3)}{row}"


def shift_ref(text: str, own_sheet: str, target: str, idx: int, n: int) -> str:
    """Desplaza una referencia (A1, $A$1:B9, 'Hoja'!A1, 5:7) si apunta a la hoja ``target``."""
    m = _RX_SHEET.match(text)
    if not m:
        return text
    sheet = m.group("sheet")
    if (_unquote(sheet) if sheet else own_sheet) != target:
        return text
    ref = m.group("ref")
    parts = ref.split(":")
    if not all(_RX_PART.match(p) for p in parts):
        return text  # nombre definido u otra cosa
    shifted = ":".join(_shift_part(p, idx, n) for p in parts)
    return f"{sheet}!{shifted}" if sheet else shifted


def shift_formula(formula: str, own_sheet: str, target: str, idx: int, n: int) -> str:
    if not isinstance(formula, str) or not formula.startswith("="):
        return formula
    try:
        tok = Tokenizer(formula)
    except Exception:  # noqa: BLE001 — fórmula que el tokenizador no entiende: se deja igual
        return formula
    changed = False
    for t in tok.items:
        if t.type == Token.OPERAND and t.subtype == Token.RANGE:
            new = shift_ref(t.value, own_sheet, target, idx, n)
            if new != t.value:
                t.value, changed = new, True
    return tok.render() if changed else formula


def _shift_sqref(sqref, idx: int, n: int) -> str:
    out = []
    for rng in str(sqref).split():
        parts = rng.split(":")
        out.append(":".join(_shift_part(p, idx, n) for p in parts))
    return " ".join(out)


def _shift_anchor(anchor, idx: int, n: int) -> None:
    for marker in (getattr(anchor, "_from", None), getattr(anchor, "to", None)):
        if marker is not None and marker.row + 1 >= idx:  # el marcador cuenta desde 0
            marker.row += n


def insert_rows(wb, ws, idx: int, n: int) -> None:
    """Inserta ``n`` filas vacías antes de ``idx`` y desplaza todo lo que depende de las filas de abajo."""
    if n <= 0:
        return
    title = ws.title
    for rng in ws.merged_cells.ranges:
        if rng.min_row < idx <= rng.max_row:
            raise ShiftError(f"La celda combinada {rng.coord} cruza la fila {idx}.")

    ws.insert_rows(idx, n)

    # celdas combinadas: primero se quitan todas las que bajan y después se agregan desplazadas
    # (``MultiCellRange.add`` ignora un rango que «ya está» si otro aún no desplazado ocupa esas celdas)
    moving = [rng for rng in ws.merged_cells.ranges if rng.min_row >= idx]
    for rng in moving:
        ws.merged_cells.ranges.discard(rng)
    for rng in moving:
        rng.shift(row_shift=n)
        ws.merged_cells.ranges.add(rng)

    # altos de fila, filas ocultas y niveles de esquema
    dims = dict(ws.row_dimensions.items())
    for key in list(ws.row_dimensions.keys()):
        del ws.row_dimensions[key]
    for r, dim in sorted(dims.items()):
        new = r + n if r >= idx else r
        dim.index = new
        ws.row_dimensions[new] = dim

    # fórmulas de todas las hojas que apuntan a esta
    for sheet in wb.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                v = cell.value
                if isinstance(v, ArrayFormula):
                    v.text = shift_formula(v.text, sheet.title, title, idx, n)
                    if sheet.title == title:
                        v.ref = _shift_sqref(v.ref, idx, n)
                elif cell.data_type == "f" and isinstance(v, str):
                    new = shift_formula(v, sheet.title, title, idx, n)
                    if new != v:
                        cell.value = new

    # formato condicional
    from openpyxl.formatting.formatting import ConditionalFormattingList

    old_cf = ws.conditional_formatting
    new_cf = ConditionalFormattingList()
    for cf in old_cf:
        sqref = _shift_sqref(cf.sqref, idx, n)
        for rule in cf.rules:
            if getattr(rule, "formula", None):
                rule.formula = [shift_formula("=" + f, title, title, idx, n)[1:] for f in rule.formula]
            new_cf.add(sqref, rule)
    ws.conditional_formatting = new_cf

    # validaciones de datos
    for dv in ws.data_validations.dataValidation:
        dv.sqref = type(dv.sqref)(_shift_sqref(dv.sqref, idx, n))
        for attr in ("formula1", "formula2"):
            f = getattr(dv, attr, None)
            if isinstance(f, str) and f and not f.startswith('"'):
                setattr(dv, attr, shift_formula("=" + f, title, title, idx, n)[1:])

    # área de impresión, títulos, autofiltro, saltos de página
    area = ws.print_area
    if area:
        parts = [shift_ref(a.strip(), title, title, idx, n).split("!")[-1] for a in str(area).split(",")]
        ws.print_area = parts
    if ws.auto_filter and ws.auto_filter.ref:
        ws.auto_filter.ref = _shift_sqref(ws.auto_filter.ref, idx, n)
    for brk in getattr(ws.row_breaks, "brk", []) or []:
        if brk.id >= idx:
            brk.id += n

    # nombres definidos (del libro y de la hoja)
    def _names(container):
        try:
            return list(container.values())
        except AttributeError:
            return list(getattr(container, "definedName", []) or [])

    for dn in _names(wb.defined_names) + _names(getattr(ws, "defined_names", {}) or {}):
        text = getattr(dn, "attr_text", None)
        if text:
            dn.attr_text = shift_formula("=" + text, title, title, idx, n)[1:]

    # imágenes y gráficos
    for obj in list(getattr(ws, "_images", [])) + list(getattr(ws, "_charts", [])):
        anchor = obj.anchor
        if isinstance(anchor, str):
            obj.anchor = _shift_part(anchor, idx, n)
        else:
            _shift_anchor(anchor, idx, n)


def copy_row_format(ws, src_row: int, dst_row: int, max_col: int, formulas: bool = True) -> None:
    """Da a ``dst_row`` el formato de ``src_row`` (estilos, alto, combinadas de la fila y, si se pide, fórmulas por fila)."""
    for c in range(1, max_col + 1):
        src = ws.cell(row=src_row, column=c)
        dst = ws.cell(row=dst_row, column=c)
        if isinstance(dst, MergedCell):
            continue
        if src.has_style:
            dst._style = copy(src._style)
        if formulas and src.data_type == "f" and isinstance(src.value, str):
            dst.value = Translator(src.value, origin=src.coordinate).translate_formula(dst.coordinate)
    h = ws.row_dimensions[src_row].height
    if h:
        ws.row_dimensions[dst_row].height = h
    for rng in list(ws.merged_cells.ranges):
        if rng.min_row == rng.max_row == src_row:
            ws.merge_cells(start_row=dst_row, start_column=rng.min_col, end_row=dst_row, end_column=rng.max_col)


def set_column_width(ws, col: int, width: float) -> None:
    """Ancho de una columna; si está dentro de un grupo de anchos (``<col min=3 max=4>``) el grupo se separa."""
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.dimensions import ColumnDimension

    for key, dim in list(ws.column_dimensions.items()):
        if dim.min and dim.max and dim.min <= col <= dim.max and dim.min != dim.max:
            del ws.column_dimensions[key]
            for k in range(dim.min, dim.max + 1):
                letter = get_column_letter(k)
                nd = ColumnDimension(ws, index=letter, width=dim.width, hidden=dim.hidden, outlineLevel=dim.outlineLevel,
                                     collapsed=dim.collapsed)
                nd._style = copy(dim._style)
                nd.min = nd.max = k
                ws.column_dimensions[letter] = nd
            break
    letter = get_column_letter(col)
    dim = ws.column_dimensions[letter]
    dim.min = dim.max = col
    dim.width = width


def row_map(shifts: list[tuple[str, int, int]], sheet: str, row: int) -> int:
    for title, idx, n in shifts:
        if title == sheet and row >= idx:
            row += n
    return row


def shift_formula_all(formula: str, own_sheet: str, shifts: list[tuple[str, int, int]]) -> str:
    for title, idx, n in shifts:
        formula = shift_formula(formula, own_sheet, title, idx, n)
    return formula


def shifted_merges(ranges, sheet: str, shifts: list[tuple[str, int, int]]) -> set[str]:
    out = set()
    for rng in ranges:
        r = CellRange(str(rng))
        for title, idx, n in shifts:
            if title == sheet and r.min_row >= idx:
                r.shift(row_shift=n)
        out.add(r.coord)
    return out
