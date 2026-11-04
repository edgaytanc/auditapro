"""Escritura controlada en una COPIA del papel de trabajo de la firma (guía §8).

Reglas que este módulo hace cumplir por código:
- El original nunca se abre para escribir: se lee, se modifica en memoria y se guarda con otro nombre.
- Una celda con fórmula jamás se sobrescribe (ni siquiera con «sobrescribir»).
- Se verifica que el rango destino esté vacío; si no, se usa la siguiente celda libre o se cancela.
- Todo texto que venga de un documento y empiece con «=» se guarda como texto, nunca como fórmula.
- Tras guardar se compara la copia contra el original; si algo cambió fuera del rango escrito,
  el archivo no se entrega.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

from .shared import Fig, Table, plain

BLUE = "FF1D4FBE"
FILL = {"ok": "FFE7F7EC", "error": "FFFDE2E2", "warn": "FFFEF3E2"}
HEADING_RX = re.compile(r"resultado|conclusi|procedimiento|hallazgo|cruce|an[aá]lisis", re.I)
MAX_CELL_CHARS = 32000
COMMENT_AUTHOR = "Audita Análisis"


class FillError(Exception):
    """No se pudo llenar el papel de trabajo; el mensaje se muestra al auditor."""


@dataclass
class TemplateInfo:
    sheets: list[str]
    text_sample: str
    risks: list[str]
    formulas: int
    proposals: dict[str, str]
    is_macro: bool


@dataclass
class PasteOptions:
    sheet: str | None = None
    start: str | None = None
    conflict: str = "siguiente_libre"  # siguiente_libre | cancelar | sobrescribir
    include_conclusion: bool = True
    include_evidence: bool = True


@dataclass
class FigureRecord:
    sheet: str
    cell: str
    fig: Fig


@dataclass
class FillReport:
    sheet: str
    start_cell: str
    end_cell: str
    cells_written: int
    figures: list[FigureRecord] = field(default_factory=list)
    addresses: dict[str, list[str]] = field(default_factory=dict)  # table.key -> celda inicial de cada fila
    evidence_sheet: str = ""
    formulas_overwritten: int = 0
    moved_from: str = ""
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- inspección

_RISK_PARTS = {
    "xl/charts/": "contiene gráficos (pueden no conservarse al llenar la copia)",
    "xl/pivotTables/": "contiene tablas dinámicas (pueden no conservarse)",
    "xl/slicers/": "contiene segmentaciones de datos (pueden no conservarse)",
    "xl/externalLinks/": "tiene vínculos a otros libros",
    "xl/ctrlProps/": "tiene controles de formulario (pueden no conservarse)",
    "xl/activeX/": "tiene controles ActiveX (pueden no conservarse)",
    "xl/threadedComments/": "tiene comentarios encadenados (pueden no conservarse)",
}


def _template_risks(path: str | Path) -> tuple[list[str], bool]:
    risks, macro = [], False
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    for prefix, message in _RISK_PARTS.items():
        if any(n.startswith(prefix) for n in names):
            risks.append(message)
    if any(n.startswith("xl/media/") for n in names):
        risks.append("contiene imágenes (pueden no conservarse)")
    if "xl/vbaProject.bin" in names:
        macro = True
    return risks, macro


def _last_used_row(ws) -> int:
    last = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value not in (None, ""):
                last = max(last, cell.row)
    return last


def propose_start(ws) -> str:
    """Primera celda libre bajo el encabezado: columna A, debajo del último contenido."""
    last = _last_used_row(ws)
    if last == 0:
        return "A1"
    last_text = " ".join(str(c.value) for c in ws[last] if isinstance(c.value, str))
    return f"A{last + 1 if HEADING_RX.search(last_text) else last + 2}"


def inspect_template(path: str | Path) -> TemplateInfo:
    risks, macro = _template_risks(path)
    wb = load_workbook(path, keep_vba=macro)
    try:
        texts, formulas, proposals = [], 0, {}
        for ws in wb.worksheets:
            texts.append(ws.title)
            for r_idx, row in enumerate(ws.iter_rows(), start=1):
                for cell in row:
                    v = cell.value
                    if isinstance(v, str):
                        if cell.data_type == "f":
                            formulas += 1
                        elif r_idx <= 80:
                            texts.append(v)
                    elif cell.data_type == "f":
                        formulas += 1
            proposals[ws.title] = propose_start(ws)
        return TemplateInfo(
            sheets=[ws.title for ws in wb.worksheets],
            text_sample=" ".join(texts)[:6000],
            risks=risks,
            formulas=formulas,
            proposals=proposals,
            is_macro=macro,
        )
    finally:
        wb.close()


# --------------------------------------------------------------------------- escritura

def _safe_text(value: str) -> str:
    return value[:MAX_CELL_CHARS]


def _set(cell, value) -> None:
    if isinstance(value, str):
        value = _safe_text(value)
        cell.value = value
        if value.startswith("="):
            cell.data_type = "s"  # nunca interpretar texto de un documento como fórmula
        return
    cell.value = value


def _style_value(cell, value) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (Decimal, float)):
        cell.number_format = "#,##0.00"
    elif isinstance(value, int):
        cell.number_format = "0"
    elif isinstance(value, (date, datetime)):
        cell.number_format = "dd/mm/yyyy"


def _merged_cells(ws) -> set[tuple[int, int]]:
    cells = set()
    for rng in ws.merged_cells.ranges:
        min_col, min_row, max_col, max_row = range_boundaries(str(rng))
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                cells.add((r, c))
    return cells


@dataclass
class _Block:
    title: str
    table: Table | None = None
    lines: list[str] = field(default_factory=list)


def _layout(blocks: list[_Block]) -> tuple[int, int]:
    """Alto y ancho (en celdas) del bloque completo a escribir."""
    height, width = 0, 1
    for b in blocks:
        height += 1  # título
        if b.table:
            width = max(width, len(b.table.head))
            height += 1 + len(b.table.rows) + (1 if b.table.truncated else 0)
            if b.table.note:
                height += 1
        height += len(b.lines)
        height += 1  # fila en blanco
    return height, width


def _region_state(ws, r0: int, c0: int, h: int, w: int, merged: set) -> tuple[list[str], list[str], list[str]]:
    """(celdas con valor, celdas con fórmula, celdas combinadas) dentro del rango."""
    values, formulas, in_merge = [], [], []
    for r in range(r0, r0 + h):
        for c in range(c0, c0 + w):
            addr = f"{get_column_letter(c)}{r}"
            cell = ws.cell(row=r, column=c)
            if cell.data_type == "f":
                formulas.append(addr)
            elif cell.value not in (None, ""):
                values.append(addr)
            if (r, c) in merged:
                in_merge.append(addr)
    return values, formulas, in_merge


def _find_free(ws, r0: int, c0: int, h: int, w: int, merged: set) -> int:
    """Primera fila ≥ r0 desde la que el rango completo está libre."""
    limit = max(ws.max_row, r0) + 2
    r = r0
    while r <= limit:
        values, formulas, in_merge = _region_state(ws, r, c0, h, w, merged)
        if not (values or formulas or in_merge):
            return r
        r += 1
    return limit


def _parse_cell(ref: str) -> tuple[int, int]:
    try:
        col, row = coordinate_from_string(ref.strip().upper())
        return row, column_index_from_string(col)
    except Exception:  # noqa: BLE001
        raise FillError("Celda de inicio no válida (ejemplo: A8).") from None


def build_blocks(tables: list[Table], conclusion: str, summary_line: str, sources_line: str, include_conclusion: bool) -> list[_Block]:
    blocks: list[_Block] = []
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for t in tables:
        blocks.append(_Block(title=f"{next(letters)}. {t.title.upper()}", table=t))
    tail = []
    if summary_line:
        tail.append(summary_line)
    if include_conclusion and conclusion:
        tail.append(f"Conclusión preliminar: {conclusion}")
    if sources_line:
        tail.append(sources_line)
    if tail:
        blocks.append(_Block(title="RESUMEN Y FUENTES", lines=tail))
    return blocks


def fill_template(
    src: str | Path,
    out: str | Path,
    *,
    tables: list[Table],
    conclusion: str,
    summary_line: str,
    sources_line: str,
    evidence_rows: list[list],
    evidence_note: str,
    options: PasteOptions,
    figure_prefix: str = "C",
) -> FillReport:
    src, out = Path(src), Path(out)
    if src.resolve() == out.resolve():
        raise FillError("El archivo de salida no puede ser el original.")
    _, macro = _template_risks(src)
    wb = load_workbook(src, keep_vba=macro)
    try:
        ws = wb[options.sheet] if options.sheet else wb.worksheets[0]
    except KeyError:
        raise FillError(f"La hoja «{options.sheet}» no existe en el papel de trabajo.") from None

    blocks = build_blocks(tables, conclusion, summary_line, sources_line, options.include_conclusion)
    height, width = _layout(blocks)
    start_ref = options.start or propose_start(ws)
    r0, c0 = _parse_cell(start_ref)
    merged = _merged_cells(ws)
    report = FillReport(sheet=ws.title, start_cell=start_ref.upper(), end_cell="", cells_written=0)

    values, formulas, in_merge = _region_state(ws, r0, c0, height, width, merged)
    if values or formulas or in_merge:
        if options.conflict == "cancelar":
            raise FillError(
                f"El rango de destino en {ws.title}!{start_ref.upper()} no está vacío; se canceló sin escribir."
            )
        if options.conflict == "sobrescribir" and not (formulas or in_merge):
            report.warnings.append(f"Se sobrescribieron {len(values)} celdas de {ws.title} (texto o números, sin fórmulas).")
        else:
            if options.conflict == "sobrescribir":
                report.warnings.append("El destino tenía fórmulas o celdas combinadas, que nunca se sobrescriben.")
            new_r = _find_free(ws, r0, c0, height, width, merged)
            report.moved_from = f"{ws.title}!{start_ref.upper()}"
            r0 = new_r
            report.start_cell = f"{get_column_letter(c0)}{r0}"

    thin = Font(italic=True, color="FF6B7280")
    row = r0
    counter = 0
    written = 0
    for block in blocks:
        title_cell = ws.cell(row=row, column=c0)
        _set(title_cell, block.title)
        title_cell.font = Font(bold=True, color=BLUE)
        written += 1
        row += 1
        if block.table:
            t = block.table
            for j, label in enumerate(t.head):
                cell = ws.cell(row=row, column=c0 + j)
                _set(cell, label)
                cell.font = Font(bold=True, color="FFFFFFFF")
                cell.fill = PatternFill("solid", fgColor=BLUE)
                cell.alignment = Alignment(wrap_text=True, vertical="center")
                written += 1
            row += 1
            report.addresses[t.key] = []
            for cells, flag in zip(t.rows, t.flags or [""] * len(t.rows)):
                report.addresses[t.key].append(f"{ws.title}!{get_column_letter(c0)}{row}")
                for j, raw in enumerate(cells):
                    cell = ws.cell(row=row, column=c0 + j)
                    value = plain(raw)
                    if value is None or value == "":
                        value = None
                    _set(cell, value)
                    if value is not None:
                        _style_value(cell, value)
                    if flag in FILL:
                        cell.fill = PatternFill("solid", fgColor=FILL[flag])
                    if flag == "total":
                        cell.font = Font(bold=True)
                    if j == len(t.head) - 1 and "origen" in t.head[j].lower():
                        cell.font = thin
                    if isinstance(raw, Fig):
                        counter += 1
                        addr = f"{get_column_letter(c0 + j)}{row}"
                        cid = raw.fid or f"{figure_prefix}-{counter:04d}"
                        cell.comment = Comment(f"{cid} · Origen: {raw.origin()}", COMMENT_AUTHOR, height=70, width=260)
                        report.figures.append(FigureRecord(sheet=ws.title, cell=addr, fig=raw))
                    written += 1
                row += 1
            if t.truncated:
                note = ws.cell(row=row, column=c0)
                _set(note, f"… y {t.truncated:,} filas más no se muestran aquí (ver los resultados completos en Audita Análisis).")
                note.font = thin
                row += 1
            if t.note:
                note = ws.cell(row=row, column=c0)
                _set(note, t.note)
                note.font = Font(italic=True, size=9, color="FF6B7280")
                row += 1
        for line in block.lines:
            cell = ws.cell(row=row, column=c0)
            _set(cell, line)
            cell.alignment = Alignment(wrap_text=False)
            written += 1
            row += 1
        row += 1

    report.end_cell = f"{get_column_letter(c0 + width - 1)}{row - 2}"
    report.cells_written = written

    if options.include_evidence and evidence_rows is not None:
        name, k = "Evidencia", 2
        while name in wb.sheetnames:
            name = f"Evidencia {k}"
            k += 1
        ev = wb.create_sheet(name)
        head = ["Documento", "Página", "Tipo", "Campo", "Valor", "Método", "Cifra"]
        for j, label in enumerate(head, start=1):
            cell = ev.cell(row=1, column=j)
            cell.value = label
            cell.font = Font(bold=True, color="FFFFFFFF")
            cell.fill = PatternFill("solid", fgColor=BLUE)
        for i, rec in enumerate(evidence_rows, start=2):
            for j, value in enumerate(rec, start=1):
                _set(ev.cell(row=i, column=j), plain(value))
        ev.cell(row=len(evidence_rows) + 3, column=1).value = evidence_note
        for col, width_ in zip("ABCDEFG", (34, 8, 22, 20, 30, 10, 10)):
            ev.column_dimensions[col].width = width_
        report.evidence_sheet = name

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    wb.close()

    region = (ws.title, r0, c0, row - r0, width)
    problems = verify_copy(src, out, written_region=region, evidence_sheet=report.evidence_sheet)
    if problems:
        out.unlink(missing_ok=True)
        raise FillError("La copia no pasó la verificación y no se entrega: " + "; ".join(problems[:3]))
    return report


# --------------------------------------------------------------------------- verificación

def verify_copy(src: str | Path, out: str | Path, *, written_region: tuple, evidence_sheet: str = "") -> list[str]:
    """Compara la copia con el original. Solo puede diferir el rango escrito y la hoja de evidencia."""
    sheet_name, r0, c0, h, w = written_region
    problems: list[str] = []
    _, macro = _template_risks(src)
    a = load_workbook(src, keep_vba=macro)
    try:
        b = load_workbook(out, keep_vba=macro)
    except Exception:  # noqa: BLE001
        return ["el archivo generado no se puede abrir"]
    try:
        names_a = a.sheetnames
        expected = names_a + ([evidence_sheet] if evidence_sheet else [])
        if b.sheetnames != expected:
            problems.append("cambió la lista de hojas")
            return problems
        for ws_a in a.worksheets:
            ws_b = b[ws_a.title]
            if {str(r) for r in ws_a.merged_cells.ranges} - {str(r) for r in ws_b.merged_cells.ranges}:
                problems.append(f"se perdieron celdas combinadas en {ws_a.title}")
            for row in ws_a.iter_rows():
                for cell in row:
                    if cell.value in (None, ""):
                        continue
                    inside = (
                        ws_a.title == sheet_name and r0 <= cell.row < r0 + h and c0 <= cell.column < c0 + w
                    )
                    other = ws_b.cell(row=cell.row, column=cell.column)
                    if cell.value != other.value or cell.data_type != other.data_type:
                        if inside and cell.data_type != "f":
                            continue  # solo se permite en «sobrescribir» y ya se advirtió; una fórmula, nunca
                        problems.append(f"cambió {ws_a.title}!{cell.coordinate}")
                        if len(problems) >= 5:
                            return problems
    finally:
        a.close()
        b.close()
    return problems
