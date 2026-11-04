"""Lectores de Excel, CSV, Word y PDF con límites para no sobrecargar el servidor.

Los límites son parámetros: si un archivo los supera, se lee hasta el límite y se
registra una advertencia visible (nunca se descarta en silencio).
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import parse_amount, parse_date

MIN_PDF_TEXT = 20  # menos caracteres por página => se trata como escaneada


@dataclass
class Limits:
    max_rows: int = 100_000
    max_pdf_pages: int = 300
    max_sheets: int = 12
    max_page_chars: int = 200_000


@dataclass
class Row:
    n: int
    values: list


@dataclass
class Tabular:
    sheet: str
    headers: list[str]
    rows: list[Row]
    header_row: int = 1
    truncated: bool = False

    def column_index(self, name: str) -> int:
        try:
            return self.headers.index(name)
        except ValueError:
            return -1


@dataclass
class Page:
    number: int
    text: str
    method: str = "texto"  # texto | sin_texto


@dataclass
class SourceDoc:
    name: str
    kind: str  # excel | csv | word | pdf | imagen
    path: str = ""
    tabular: list[Tabular] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def main_table(self) -> Tabular | None:
        """La hoja con más filas (la que normalmente es el auxiliar)."""
        if not self.tabular:
            return None
        return max(self.tabular, key=lambda t: len(t.rows))


KIND_BY_EXT = {
    ".xlsx": "excel",
    ".xlsm": "excel",
    ".csv": "csv",
    ".docx": "word",
    ".pdf": "pdf",
    ".png": "imagen",
    ".jpg": "imagen",
    ".jpeg": "imagen",
    ".tif": "imagen",
    ".tiff": "imagen",
}


def kind_for(name: str) -> str | None:
    return KIND_BY_EXT.get(Path(name).suffix.lower())


# ------------------------------------------------------------------ encabezados

def _clean(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def detect_header(rows: list[tuple[int, list]]) -> int:
    """Índice (dentro de ``rows``) de la fila de encabezado.

    Primera fila, entre las 30 primeras con datos, que tenga al menos 2 celdas de texto
    y cuyo texto sea mayoría de sus celdas no vacías (descarta títulos de una celda).
    """
    for idx, (_, values) in enumerate(rows[:30]):
        filled = [v for v in values if not _is_blank(v)]
        texts = [v for v in filled if isinstance(v, str) and parse_amount(v) is None]
        if len(texts) >= 2 and len(texts) >= 0.6 * len(filled):
            return idx
    return 0


def _build_tabular(sheet: str, raw: list[tuple[int, list]], limits: Limits, truncated: bool) -> Tabular | None:
    raw = [(n, v) for n, v in raw if any(not _is_blank(c) for c in v)]
    if not raw:
        return None
    h = detect_header(raw)
    header_n, header_vals = raw[h]
    headers = []
    for i, value in enumerate(header_vals):
        label = str(value).strip() if not _is_blank(value) else f"Columna {i + 1}"
        headers.append(label)
    width = len(headers)
    rows = []
    for n, values in raw[h + 1:]:
        padded = list(values[:width]) + [None] * (width - len(values))
        rows.append(Row(n=n, values=[_clean(c) for c in padded]))
    return Tabular(sheet=sheet, headers=headers, rows=rows, header_row=header_n, truncated=truncated)


# ------------------------------------------------------------------ Excel / CSV

def _read_excel(doc: SourceDoc, limits: Limits) -> None:
    from openpyxl import load_workbook

    wb = load_workbook(doc.path, read_only=True, data_only=True)
    try:
        budget = limits.max_rows
        for ws in wb.worksheets[: limits.max_sheets]:
            raw: list[tuple[int, list]] = []
            empty_streak = 0
            truncated = False
            for n, values in enumerate(ws.iter_rows(values_only=True), start=1):
                values = list(values)
                if all(_is_blank(c) for c in values):
                    empty_streak += 1
                    if empty_streak >= 1000:
                        break
                    continue
                empty_streak = 0
                if budget <= 0:
                    truncated = True
                    break
                raw.append((n, values))
                budget -= 1
            table = _build_tabular(ws.title, raw, limits, truncated)
            if table:
                doc.tabular.append(table)
            if truncated:
                doc.warnings.append(
                    f"Hoja «{ws.title}»: se leyeron solo las primeras {limits.max_rows:,} filas (límite del sistema)."
                )
        if len(wb.worksheets) > limits.max_sheets:
            doc.warnings.append(f"Solo se leyeron las primeras {limits.max_sheets} hojas.")
    finally:
        wb.close()
    if not doc.tabular:
        doc.warnings.append("El Excel no tiene filas con datos.")


def _decode_csv(path: str) -> str:
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _read_csv(doc: SourceDoc, limits: Limits) -> None:
    text = _decode_csv(doc.path)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), dialect)
    raw: list[tuple[int, list]] = []
    truncated = False
    for n, values in enumerate(reader, start=1):
        if len(raw) >= limits.max_rows:
            truncated = True
            break
        raw.append((n, values))
    table = _build_tabular(Path(doc.name).stem, raw, limits, truncated)
    if table:
        doc.tabular.append(table)
    else:
        doc.warnings.append("El CSV no tiene filas con datos.")
    if truncated:
        doc.warnings.append(f"Se leyeron solo las primeras {limits.max_rows:,} filas (límite del sistema).")


# ------------------------------------------------------------------ Word

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_docx(doc: SourceDoc, limits: Limits) -> None:
    import docx
    from docx.table import Table as DocxTable
    from docx.text.paragraph import Paragraph

    document = docx.Document(doc.path)
    pages: list[list[str]] = [[]]

    def new_page():
        if pages[-1]:
            pages.append([])

    for element in document.element.body.iterchildren():
        if element.tag == f"{_W_NS}p":
            paragraph = Paragraph(element, document)
            if element.findall(f".//{_W_NS}lastRenderedPageBreak"):
                new_page()
            text = paragraph.text.strip()
            if text:
                pages[-1].append(text)
            breaks = [
                b for b in element.iter(f"{_W_NS}br") if b.get(f"{_W_NS}type") == "page"
            ]
            if breaks:
                new_page()
        elif element.tag == f"{_W_NS}tbl":
            table = DocxTable(element, document)
            for row in table.rows:
                cells = []
                for cell in row.cells:
                    value = cell.text.strip().replace("\n", " ")
                    if value and (not cells or cells[-1] != value):
                        cells.append(value)
                if cells:
                    pages[-1].append(" | ".join(cells))
    pages = [p for p in pages if p]
    for number, lines in enumerate(pages, start=1):
        doc.pages.append(Page(number=number, text="\n".join(lines)[: limits.max_page_chars]))
    if not doc.pages:
        doc.warnings.append("El documento Word no tiene texto.")
    elif len(doc.pages) > 1:
        doc.warnings.append(
            "Word no guarda páginas fijas: la página citada es la sección del documento (saltos de página)."
        )


# ------------------------------------------------------------------ PDF

def _read_pdf(doc: SourceDoc, limits: Limits) -> None:
    import pdfplumber

    with pdfplumber.open(doc.path) as pdf:
        total = len(pdf.pages)
        for index, page in enumerate(pdf.pages[: limits.max_pdf_pages], start=1):
            text = (page.extract_text() or "").strip()
            if len(text) < MIN_PDF_TEXT:
                doc.pages.append(Page(number=index, text="", method="sin_texto"))
            else:
                doc.pages.append(Page(number=index, text=text[: limits.max_page_chars]))
            page.flush_cache()
        if total > limits.max_pdf_pages:
            doc.warnings.append(
                f"El PDF tiene {total} páginas: se leyeron las primeras {limits.max_pdf_pages} (límite del sistema)."
            )
    scanned = [p.number for p in doc.pages if p.method == "sin_texto"]
    if scanned:
        shown = ", ".join(str(n) for n in scanned[:10])
        doc.warnings.append(
            f"{len(scanned)} página(s) sin texto (escaneadas o imágenes): {shown}"
            f"{'…' if len(scanned) > 10 else ''}. Quedan como evidencia; requieren OCR o revisión manual."
        )


def find_pdf_bbox(path: str, page_number: int, needle: str) -> dict | None:
    """Rectángulo (puntos PDF) de la primera aparición de ``needle`` en una página."""
    import pdfplumber

    if not needle:
        return None
    try:
        with pdfplumber.open(path) as pdf:
            if not 1 <= page_number <= len(pdf.pages):
                return None
            page = pdf.pages[page_number - 1]
            matches = page.search(re.escape(needle), regex=True, case=False)
            if not matches:
                return None
            m = matches[0]
            return {
                "x0": round(m["x0"], 2),
                "top": round(m["top"], 2),
                "x1": round(m["x1"], 2),
                "bottom": round(m["bottom"], 2),
                "page_width": round(float(page.width), 2),
                "page_height": round(float(page.height), 2),
            }
    except Exception:  # noqa: BLE001 - la coordenada es un extra, nunca debe romper el análisis
        return None


def find_pdf_bboxes(path: str, items: list[tuple[int, str]], cap: int = 400) -> dict[tuple[int, str], dict]:
    """Coordenadas de varios valores abriendo el PDF una sola vez."""
    import pdfplumber

    found: dict[tuple[int, str], dict] = {}
    wanted = [(p, n) for p, n in dict.fromkeys(items) if n][:cap]
    if not wanted:
        return found
    try:
        with pdfplumber.open(path) as pdf:
            for page_number, needle in wanted:
                if not 1 <= page_number <= len(pdf.pages):
                    continue
                page = pdf.pages[page_number - 1]
                matches = page.search(re.escape(needle), regex=True, case=False)
                if matches:
                    m = matches[0]
                    found[(page_number, needle)] = {
                        "x0": round(m["x0"], 2), "top": round(m["top"], 2),
                        "x1": round(m["x1"], 2), "bottom": round(m["bottom"], 2),
                        "page_width": round(float(page.width), 2), "page_height": round(float(page.height), 2),
                    }
    except Exception:  # noqa: BLE001 - la coordenada es un extra, nunca debe romper el análisis
        return found
    return found


# ------------------------------------------------------------------ API

def read_document(path: str, name: str, limits: Limits | None = None) -> SourceDoc:
    """Lee un archivo ya validado. Los errores quedan en ``doc.error``."""
    limits = limits or Limits()
    kind = kind_for(name)
    doc = SourceDoc(name=name, kind=kind or "otro", path=path)
    try:
        if kind == "excel":
            _read_excel(doc, limits)
        elif kind == "csv":
            _read_csv(doc, limits)
        elif kind == "word":
            _read_docx(doc, limits)
        elif kind == "pdf":
            _read_pdf(doc, limits)
        elif kind == "imagen":
            doc.pages.append(Page(number=1, text="", method="sin_texto"))
            doc.warnings.append("Imagen sin texto: queda como evidencia; requiere OCR o revisión manual.")
        else:
            doc.error = "Formato no admitido."
    except Exception as exc:  # noqa: BLE001
        doc.error = f"No se pudo leer el archivo ({type(exc).__name__})."
    return doc


def cell_value(row: Row, index: int):
    if index < 0 or index >= len(row.values):
        return None
    return row.values[index]


__all__ = [
    "Limits", "Row", "Tabular", "Page", "SourceDoc", "read_document", "kind_for",
    "find_pdf_bbox", "cell_value", "parse_date",
]
