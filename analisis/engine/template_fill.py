"""Escritura controlada en una COPIA del papel de trabajo de la firma (guía §8).

Reglas que este módulo hace cumplir por código:
- El original nunca se abre para escribir: se lee, se modifica en memoria y se guarda con otro nombre.
- Una celda con fórmula jamás se sobrescribe (ni siquiera con «sobrescribir»).
- Se verifica que el rango destino esté vacío; si no, se usa la siguiente celda libre o se cancela.
- Todo texto que venga de un documento y empiece con «=» se guarda como texto, nunca como fórmula.
- Tras guardar se compara la copia contra el original; si algo cambió fuera del rango escrito,
  el archivo no se entrega.
- Se comparan además las partes del archivo (formas, imágenes, gráficos, formato condicional, validaciones…):
  lo que la copia no conserve se advierte con precisión, para que el auditor lo revise contra el original.
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
    structure: dict = field(default_factory=dict)  # tabla del papel llenada (ver structured_fill)


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
    structure: dict | None = None,
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

    # 1) la tabla propia del papel (cada transacción en sus columnas); si se llenó, el resto va en hoja aparte
    struct = None
    if structure:
        from .structured_fill import ANALYSIS_SHEET, fill_structure

        struct = fill_structure(
            wb, detail=structure.get("detail"), monthly=structure.get("monthly"), ledger_total=structure.get("ledger_total"),
            observations=structure.get("observations") or [], conclusion=conclusion,
            results_anchor=f"la hoja «{ANALYSIS_SHEET}»", source=structure.get("source"),
            source_name=structure.get("source_name") or "",
        )
        if struct.detail:
            name, k = ANALYSIS_SHEET, 2
            while name in wb.sheetnames:
                name = f"{ANALYSIS_SHEET} {k}"
                k += 1
            ws = wb.create_sheet(name)
            ws.column_dimensions["A"].width = 38
            for col in "BCDEFGHIJKLMN":
                ws.column_dimensions[col].width = 17
            options = PasteOptions(sheet=name, start="A1", conflict="cancelar", include_conclusion=options.include_conclusion,
                                   include_evidence=options.include_evidence)

    start_ref = options.start or propose_start(ws)
    r0, c0 = _parse_cell(start_ref)
    merged = _merged_cells(ws)
    report = FillReport(sheet=ws.title, start_cell=start_ref.upper(), end_cell="", cells_written=0)
    if struct is not None:
        report.warnings.extend(struct.warnings)
        if struct.detail:
            report.structure = struct.summary()
            report.structure["hoja_analisis"] = ws.title
            for sheet_name, addr, fig in struct.figures:
                report.figures.append(FigureRecord(sheet=sheet_name, cell=addr, fig=fig))

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
    if struct is not None and struct.detail:
        # hoja «ANÁLISIS AGENTES»: cada columna al ancho de su contenido (los títulos de bloque no cuentan)
        longest: dict[int, int] = {}
        for cells in ws.iter_rows(min_row=1, max_row=row):
            filled = [c for c in cells if c.value not in (None, "")]
            if len(filled) <= 1:
                continue
            for c in filled:
                text = f"{c.value:,.2f}" if isinstance(c.value, float) else str(c.value)
                longest[c.column] = max(longest.get(c.column, 0), len(text))
        for col, n in longest.items():
            ws.column_dimensions[get_column_letter(col)].width = max(10, min(n * 1.05 + 2, 50))
        for cells in ws.iter_rows(min_row=1, max_row=row):
            for c in cells:
                if isinstance(c.value, str) and len(c.value) > 50 and c.font and not c.font.b:
                    c.alignment = Alignment(wrap_text=False, vertical="top")

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

    regions = [(ws.title, r0, c0, row - r0, width)]
    extra_sheets = []
    shifts, guarded = [], set()
    if struct and struct.detail:
        regions = list(struct.regions)
        if struct.detail_sheet:
            extra_sheets.append(struct.detail_sheet)
        extra_sheets.append(ws.title)  # hoja «ANÁLISIS AGENTES» (se crea después de la de detalle)
        if struct.shift:
            shifts.append(struct.shift)
        guarded = struct.guarded
    if report.evidence_sheet:
        extra_sheets.append(report.evidence_sheet)
    problems = verify_copy(src, out, written_region=regions, evidence_sheet=extra_sheets, shifts=shifts, guarded=guarded)
    if problems:
        out.unlink(missing_ok=True)
        raise FillError("La copia no pasó la verificación y no se entrega: " + "; ".join(problems[:3]))
    report.warnings.extend(lost_features(src, out))
    return report


# --------------------------------------------------------------------------- verificación

_FEATURES = (
    # (etiqueta, cómo contarla) — se cuentan en el original y en la copia
    ("forma(s) o línea(s) dibujada(s)", "drawing", re.compile(rb"<xdr:(?:sp|cxnSp)[ >]")),
    ("imagen(es)", "drawing", re.compile(rb"<xdr:pic[ >]")),
    ("gráfico(s)", "part", "xl/charts/chart"),
    ("regla(s) de formato condicional", "sheet", re.compile(rb"<(?:\w+:)?conditionalFormatting[ >]")),
    ("validación(es) de datos", "sheet", re.compile(rb"<(?:\w+:)?dataValidation[ >]")),
    ("hipervínculo(s)", "sheet", re.compile(rb"<hyperlink ")),
    ("protección(es) de hoja", "sheet", re.compile(rb"<sheetProtection")),
    ("tabla(s) de Excel", "part", "xl/tables/"),
    ("tabla(s) dinámica(s)", "part", "xl/pivotTables/"),
    ("nombre(s) definido(s)", "workbook", re.compile(rb"<definedName ")),
)


def _feature_counts(path: str | Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        cache: dict[str, bytes] = {}

        def read(prefix: str) -> list[bytes]:
            return [cache.setdefault(n, zf.read(n)) for n in names if n.startswith(prefix) and n.endswith(".xml")]

        for label, where, rule in _FEATURES:
            if where == "part":
                counts[label] = sum(1 for n in names if n.startswith(rule))
            elif where == "drawing":
                counts[label] = sum(len(rule.findall(x)) for x in read("xl/drawings/drawing"))
            elif where == "sheet":
                counts[label] = sum(len(rule.findall(x)) for x in read("xl/worksheets/sheet"))
            else:
                counts[label] = sum(len(rule.findall(x)) for x in read("xl/workbook.xml"))
    return counts


def lost_features(src: str | Path, out: str | Path) -> list[str]:
    """Lo que el original tiene y la copia no conserva (openpyxl no guarda todo lo que Excel sabe dibujar)."""
    try:
        before, after = _feature_counts(src), _feature_counts(out)
    except (zipfile.BadZipFile, KeyError, OSError):
        return []
    lost = [f"{before[k] - after.get(k, 0)} {k}" for k in before if after.get(k, 0) < before[k]]
    if not lost:
        return []
    return [
        "La copia no conserva " + ", ".join(lost) + " del original (los datos y las fórmulas sí se conservan). "
        "Revise esos elementos contra el original o cópielos a mano antes de entregar el papel."
    ]


def verify_copy(src: str | Path, out: str | Path, *, written_region, evidence_sheet="", shifts=(), guarded=()) -> list[str]:
    """Compara la copia con el original. Solo pueden diferir los rangos escritos y las hojas agregadas.

    ``written_region``: (hoja, fila, col, alto, ancho) o una lista de ellos (en filas de la copia).
    ``evidence_sheet``: nombre o lista de nombres. ``shifts``: filas insertadas ``(hoja, fila, cantidad)``: cada celda
    del original se busca en su nueva fila y cada fórmula debe ser la original desplazada como lo haría Excel.
    ``guarded``: celdas ``(hoja, celda)`` cuya fórmula se condicionó con ``=IF(celda="","",fórmula)``.
    """
    from .sheet_rows import row_map, shift_formula_all, shifted_merges

    shifts = list(shifts or [])
    guarded = set(guarded or ())
    regions = [written_region] if isinstance(written_region, tuple) else list(written_region)
    added = [evidence_sheet] if isinstance(evidence_sheet, str) else list(evidence_sheet)
    added = [n for n in added if n]

    def inside_any(title, r, c):
        return any(t == title and r0 <= r < r0 + h and c0 <= c < c0 + w for t, r0, c0, h, w in regions)

    problems: list[str] = []
    _, macro = _template_risks(src)
    a = load_workbook(src, keep_vba=macro)
    try:
        b = load_workbook(out, keep_vba=macro)
    except Exception:  # noqa: BLE001
        return ["el archivo generado no se puede abrir"]
    try:
        names_a = a.sheetnames
        expected = names_a + added
        if b.sheetnames != expected:
            problems.append("cambió la lista de hojas")
            return problems
        for ws_a in a.worksheets:
            ws_b = b[ws_a.title]
            if shifted_merges(ws_a.merged_cells.ranges, ws_a.title, shifts) - {str(r) for r in ws_b.merged_cells.ranges}:
                problems.append(f"se perdieron celdas combinadas en {ws_a.title}")
            for row in ws_a.iter_rows():
                for cell in row:
                    if cell.value in (None, ""):
                        continue
                    new_row = row_map(shifts, ws_a.title, cell.row)
                    inside = inside_any(ws_a.title, new_row, cell.column)
                    other = ws_b.cell(row=new_row, column=cell.column)
                    expected = cell.value
                    if cell.data_type == "f" and isinstance(expected, str) and shifts:
                        expected = shift_formula_all(expected, ws_a.title, shifts)
                    if expected != other.value or cell.data_type != other.data_type:
                        if inside and cell.data_type != "f":
                            continue  # dato de ejemplo sustituido dentro de la región escrita; una fórmula, nunca
                        if ((ws_a.title, other.coordinate) in guarded and isinstance(other.value, str)
                                and other.value.upper().startswith("=IF(") and other.value.endswith("," + str(expected)[1:] + ")")):
                            continue  # misma fórmula, solo condicionada a que el auditor anote el dato del que depende
                        problems.append(f"cambió {ws_a.title}!{cell.coordinate}")
                        if len(problems) >= 5:
                            return problems
    finally:
        a.close()
        b.close()
    return problems
