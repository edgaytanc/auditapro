"""Llenado dentro de la estructura del papel de trabajo (su propia tabla de detalle, cuadre y observaciones).

Se aplica solo si el papel trae una tabla de detalle reconocible:
- una fila de encabezados con **Fecha**, **Descripción/Concepto** y **Monto/Importe/Valor**;
- debajo, filas de detalle que terminan en una fila **TOTAL** con fórmula sobre la columna del monto.

Reglas (las mismas del resto del llenado):
- una fórmula nunca se toca; solo se escribe en celdas de valor dentro de las filas de detalle;
- si hay más partidas que filas, se integra por mes (cada total mensual con su origen verificable) y el
  detalle completo va en la hoja «Detalle integración»; nunca se insertan filas (romperían el =SUM del papel);
- la conclusión del auditor no se reemplaza: si ya tiene texto, se agrega un comentario con la propuesta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from openpyxl.cell.cell import MergedCell
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .shared import Fig, Table, plain

DETAIL_SHEET = "Detalle integración"
COMMENT_AUTHOR = "Audita Análisis"
BLUE = "FF1D4FBE"

ROLES = {
    "num": re.compile(r"^(no\.?|n\.?\s?[º°o]\.?|#|item|correlativo)$", re.I),
    "tipo": re.compile(r"^tipo", re.I),
    "fecha": re.compile(r"^fecha", re.I),
    "documento": re.compile(r"(no\.?|n[uú]m(ero)?\.?)\s*(de\s*)?(doc|cheque|factura|comprobante|transf)|^documento|^cheque|^comprobante", re.I),
    "proveedor": re.compile(r"proveedor|beneficiario|tercero|cliente", re.I),
    "descripcion": re.compile(r"descrip|concepto|detalle", re.I),
    "monto": re.compile(r"monto|importe|valor", re.I),
    "cuenta": re.compile(r"\bcta\b|cuenta", re.I),
    "marca": re.compile(r"^marca", re.I),
    "observaciones": re.compile(r"observ", re.I),
}
_RX_TOTAL = re.compile(r"^\s*total", re.I)
_RX_LEDGER = re.compile(r"registros contables|seg[uú]n (el )?mayor|seg[uú]n libros|saldo seg[uú]n (contabilidad|registros)", re.I)
_RX_OBS = re.compile(r"^\s*observaciones generales", re.I)
_RX_CONCL = re.compile(r"^\s*conclusi[oó]n", re.I)


@dataclass
class DetailTable:
    sheet: str
    header_row: int
    total_row: int
    columns: dict[str, int]  # rol -> columna
    first_col: int
    last_col: int

    @property
    def slots(self) -> list[int]:
        return list(range(self.header_row + 1, self.total_row))


@dataclass
class StructureReport:
    detail: DetailTable | None = None
    mode: str = ""  # partidas | mensual | ""
    rows_written: int = 0
    regions: list[tuple] = field(default_factory=list)  # (hoja, fila, col, alto, ancho) que se pueden modificar
    figures: list[tuple[str, str, Fig]] = field(default_factory=list)  # (hoja, celda, cifra)
    ledger_cell: str = ""
    observations_cell: str = ""
    conclusion_cell: str = ""
    detail_sheet: str = ""
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        d = self.detail
        return {
            "tabla": f"{d.sheet}!{get_column_letter(d.first_col)}{d.header_row + 1}:{get_column_letter(d.last_col)}{d.total_row - 1}" if d else "",
            "modo": self.mode, "filas": self.rows_written, "cuadre": self.ledger_cell,
            "observaciones": self.observations_cell, "conclusion": self.conclusion_cell, "hoja_detalle": self.detail_sheet,
        }


def _text(cell) -> str:
    v = cell.value
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) and cell.data_type != "f" else ""


def _writable(ws, row: int, col: int) -> bool:
    cell = ws.cell(row=row, column=col)
    return not isinstance(cell, MergedCell) and cell.data_type != "f"


def find_detail_table(ws, max_scan: int = 300) -> DetailTable | None:
    for r in range(1, min(ws.max_row, max_scan) + 1):
        roles: dict[str, int] = {}
        for c in range(1, min(ws.max_column, 40) + 1):
            text = _text(ws.cell(row=r, column=c))
            if not text or len(text) > 40:
                continue
            for role, rx in ROLES.items():
                if role not in roles and rx.search(text):
                    roles[role] = c
                    break
        if not {"fecha", "descripcion", "monto"} <= roles.keys():
            continue
        money = get_column_letter(roles["monto"])
        for t in range(r + 1, min(r + 400, ws.max_row) + 1):
            row_text = " ".join(_text(ws.cell(row=t, column=c)) for c in range(1, roles["monto"]))
            total = ws.cell(row=t, column=roles["monto"])
            if _RX_TOTAL.search(row_text) or (total.data_type == "f" and "SUM" in str(total.value).upper()):
                if total.data_type == "f" and money in str(total.value).upper() and t - r > 1:
                    return DetailTable(ws.title, r, t, roles, min(roles.values()), max(roles.values()))
                break
    return None


def _fit_rows(ws, row: int, lines: list[str]) -> None:
    """Agranda las filas del bloque combinado para que el texto se lea completo en Excel (solo formato)."""
    rng = next((r for r in ws.merged_cells.ranges if r.min_row == row and r.min_col == 1), None)
    last = rng.max_row if rng else row
    width_chars = 0.0
    for c in range(1, (rng.max_col if rng else 1) + 1):
        dim = next((d for d in ws.column_dimensions.values() if d.min and d.max and d.min <= c <= d.max), None)
        width_chars += dim.width if dim and dim.width else 9.14
    per_line = max(int(width_chars * 1.15), 40)  # letra de 9 pt: caben más caracteres que el ancho nominal
    needed = sum(max(1, -(-len(line) // per_line)) for line in lines) * 12.5 + 4
    current = sum((ws.row_dimensions[r].height or 15) for r in range(row, last + 1))
    if needed > current:
        extra = (needed - current) / (last - row + 1)
        for r in range(row, last + 1):
            ws.row_dimensions[r].height = (ws.row_dimensions[r].height or 15) + extra


_RX_INTEGRATION = re.compile(r"integraci[oó]n", re.I)


def is_integration_paper(ws, dt: DetailTable) -> bool:
    """Solo los papeles de INTEGRACIÓN (100 % de una población) se llenan dentro de su tabla.

    Las pruebas por muestra, arqueos o análisis especiales tienen tablas cuyas partidas elige el auditor:
    ahí los resultados van debajo del papel, como siempre.
    """
    for r in range(1, dt.header_row):
        for c in range(1, min(ws.max_column, 15) + 1):
            if _RX_INTEGRATION.search(_text(ws.cell(row=r, column=c))):
                return True
    return False


def _comment(cell, text: str) -> None:
    cell.comment = Comment(text, COMMENT_AUTHOR, height=90, width=300)


def _put(ws, report: StructureReport, row: int, col: int | None, value, *, fig: Fig | None = None, number: str = "",
         note: str = "") -> None:
    if col is None or not _writable(ws, row, col):
        return
    cell = ws.cell(row=row, column=col)
    if isinstance(value, str):
        cell.value = value[:32000]
        if value.startswith("="):
            cell.data_type = "s"
    else:
        cell.value = value
    if number:
        cell.number_format = number
    if fig is not None:
        report.figures.append((ws.title, f"{get_column_letter(col)}{row}", fig))
        _comment(cell, f"{fig.fid or 'Cifra'} · Origen: {fig.origin()}" + (f"\n{note}" if note else ""))


def fill_structure(wb, *, detail: Table | None, monthly: Table | None, ledger_total: Decimal | None,
                   observations: list[str], conclusion: str, results_anchor: str) -> StructureReport:
    report = StructureReport()
    ws = dt = None
    for sheet in wb.worksheets:
        found = find_detail_table(sheet)
        if found and is_integration_paper(sheet, found):
            ws, dt = sheet, found
            break
    if ws is None or detail is None or not detail.rows:
        return report
    cols = dt.columns
    slots = dt.slots
    total_items = len(detail.rows) + detail.truncated
    fits_items = total_items <= len(slots) and not detail.truncated
    fits_months = monthly is not None and 0 < len(monthly.rows) <= len(slots)
    if not (fits_items or fits_months):
        # no se toca nada del papel: los resultados completos van igual debajo y en «Evidencia»
        report.warnings.append(
            f"La tabla de detalle de {ws.title} tiene {len(slots)} filas y la integración necesita "
            f"{len(monthly.rows) if monthly else total_items} (meses): no se llenó la tabla del papel."
        )
        return report
    report.detail = dt

    if fits_items:
        report.mode = "partidas"
        for i, (slot, row) in enumerate(zip(slots, detail.rows), start=1):
            n, fecha, tipo, numero, proveedor, desc, cuenta, monto, marca, obs = row
            if cols.get("num") and ws.cell(row=slot, column=cols["num"]).value in (None, ""):
                _put(ws, report, slot, cols["num"], i)
            _put(ws, report, slot, cols.get("tipo"), tipo or None)
            _put(ws, report, slot, cols.get("fecha"), fecha, number="dd/mm/yyyy")
            _put(ws, report, slot, cols.get("documento"), numero or None)
            text = desc or ""
            if "proveedor" in cols:
                _put(ws, report, slot, cols["proveedor"], proveedor or None)
            else:
                text = " — ".join(x for x in (proveedor, desc) if x) + (f" · Doc. {numero}" if numero and "documento" not in cols else "")
            _put(ws, report, slot, cols.get("descripcion"), text or None)
            _put(ws, report, slot, cols.get("cuenta"), cuenta or None)
            fig = monto if isinstance(monto, Fig) else None
            _put(ws, report, slot, cols.get("monto"), float(plain(monto)), fig=fig, number="#,##0.00")
            _put(ws, report, slot, cols.get("marca"), marca or None)
            _put(ws, report, slot, cols.get("observaciones"), obs or None)
        report.rows_written = min(len(slots), len(detail.rows))
    else:
        report.mode = "mensual"
        for i, (slot, row) in enumerate(zip(slots, monthly.rows), start=1):
            key, label, count, tipo, cuenta, monto, with_alert, checked, last = row
            if cols.get("num") and ws.cell(row=slot, column=cols["num"]).value in (None, ""):
                _put(ws, report, slot, cols["num"], i)
            _put(ws, report, slot, cols.get("tipo"), tipo if tipo and tipo != "Varios" else None)
            _put(ws, report, slot, cols.get("fecha"), last, number="dd/mm/yyyy")
            _put(ws, report, slot, cols.get("descripcion"), f"{label} · {count:,} partidas")
            _put(ws, report, slot, cols.get("cuenta"), cuenta or None)
            fig = monto if isinstance(monto, Fig) else None
            _put(ws, report, slot, cols.get("monto"), float(plain(monto)), fig=fig, number="#,##0.00",
                 note=f"Suma de {count:,} partidas de {label}; detalle en la hoja «{DETAIL_SHEET}».")
            _put(ws, report, slot, cols.get("marca"), "Σ")
            notes = []
            if with_alert:
                notes.append(f"{with_alert} alerta{'s' if with_alert != 1 else ''}")
            if checked:
                notes.append(f"{checked} cotejada{'s' if checked != 1 else ''}")
            _put(ws, report, slot, cols.get("observaciones"), " · ".join(notes) or None)
        report.rows_written = len(monthly.rows)

    # filas del detalle que quedaron sin usar: se quitan las marcas de ejemplo (✓) para no dar por verificado lo vacío
    for slot in slots[report.rows_written:]:
        for role in ("marca", "tipo"):
            c = cols.get(role)
            if c and _writable(ws, slot, c) and ws.cell(row=slot, column=c).value not in (None, ""):
                ws.cell(row=slot, column=c).value = None
    report.regions.append((ws.title, slots[0], dt.first_col, len(slots), dt.last_col - dt.first_col + 1))

    # cuadre contra registros contables
    for r in range(dt.total_row + 1, min(dt.total_row + 15, ws.max_row) + 1):
        label = " ".join(_text(ws.cell(row=r, column=c)) for c in range(1, ws.max_column + 1))
        if not _RX_LEDGER.search(label):
            continue
        target = None
        for c in range(2, ws.max_column + 1):
            cell = ws.cell(row=r, column=c)
            if not isinstance(cell, MergedCell) and cell.data_type != "f" and cell.value in (None, ""):
                left = " ".join(_text(ws.cell(row=r, column=k)) for k in range(1, c))
                if _RX_LEDGER.search(left):
                    target = c
                    break
        if target:
            addr = f"{get_column_letter(target)}{r}"
            if ledger_total is not None:
                _put(ws, report, r, target, float(ledger_total), number="#,##0.00")
                _comment(ws.cell(row=r, column=target), "Saldo según el mayor ingresado por el auditor en Audita Análisis "
                                                        "(parámetro «Saldo según mayor»). La diferencia la calcula la fórmula del papel.")
                report.ledger_cell = f"{ws.title}!{addr}"
                report.regions.append((ws.title, r, target, 1, 1))
            else:
                report.warnings.append(f"Complete {ws.title}!{addr} con el total según registros contables (no se indicó el saldo del mayor).")
        break

    # observaciones generales
    for r in range(dt.total_row + 1, min(dt.total_row + 40, ws.max_row) + 1):
        if any(_RX_OBS.search(_text(ws.cell(row=r, column=c))) for c in range(1, 4)):
            tr = r + 1
            if _writable(ws, tr, 1) and ws.cell(row=tr, column=1).value in (None, ""):
                lines = observations[:8] + [
                    f"Las {total_items:,} partidas, con la observación de cada una, están en la hoja «{DETAIL_SHEET}»; "
                    f"resultados completos de Audita Análisis a partir de {results_anchor} y en la hoja «Evidencia».",
                ]
                cell = ws.cell(row=tr, column=1)
                cell.value = "\n".join(lines)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.font = Font(size=9)
                _fit_rows(ws, tr, lines)
                report.observations_cell = f"{ws.title}!A{tr}"
                report.regions.append((ws.title, tr, 1, 1, 1))
            break

    # conclusión: es del auditor; si la plantilla ya trae texto, solo se comenta
    for r in range(dt.total_row + 1, min(dt.total_row + 60, ws.max_row) + 1):
        if any(_RX_CONCL.search(_text(ws.cell(row=r, column=c))) for c in range(1, 4)):
            tr = r + 1
            if _writable(ws, tr, 1):
                cell = ws.cell(row=tr, column=1)
                proposal = f"Propuesta de Audita Análisis (pendiente de revisión del auditor): {conclusion}"
                if cell.value in (None, ""):
                    cell.value = proposal
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                    report.regions.append((ws.title, tr, 1, 1, 1))
                else:
                    _comment(cell, "Revise esta conclusión: el análisis identificó alertas.\n" + proposal[:900])
                    report.warnings.append(
                        f"La conclusión de {ws.title}!A{tr} es texto de la plantilla y no se modificó: revísela (se dejó un comentario con la propuesta)."
                    )
                report.conclusion_cell = f"{ws.title}!A{tr}"
            break

    # hoja con el detalle completo de la integración
    name = DETAIL_SHEET
    k = 2
    while name in wb.sheetnames:
        name = f"{DETAIL_SHEET} {k}"
        k += 1
    sh = wb.create_sheet(name)
    head = ["No.", "Fecha", "Tipo doc.", "No. documento", "Proveedor / beneficiario", "Descripción", "Cuenta", "Monto", "Marca",
            "Observaciones", "Origen"]
    for j, label in enumerate(head, start=1):
        c = sh.cell(row=1, column=j, value=label)
        c.font = Font(bold=True, color="FFFFFFFF")
        c.fill = PatternFill("solid", fgColor=BLUE)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    warn_fill = PatternFill("solid", fgColor="FFFEF3E2")
    for i, row in enumerate(detail.rows, start=2):
        n, fecha, tipo, numero, proveedor, desc, cuenta, monto, marca, obs = row
        values = [i - 1, fecha, tipo, numero, proveedor, desc, cuenta, float(plain(monto)), marca, obs,
                  monto.origin() if isinstance(monto, Fig) else ""]
        for j, v in enumerate(values, start=1):
            c = sh.cell(row=i, column=j)
            if isinstance(v, str) and v.startswith("="):
                c.value, c.data_type = v, "s"
            else:
                c.value = v if v != "" else None
            if j == 2 and isinstance(v, date):
                c.number_format = "dd/mm/yyyy"
            if j == 8:
                c.number_format = "#,##0.00"
            if obs and any(not part.strip().startswith("Cotejado") for part in str(obs).split(";")):
                c.fill = warn_fill
    last = len(detail.rows) + 1
    sh.cell(row=last + 1, column=1, value="TOTAL").font = Font(bold=True)
    tot = sh.cell(row=last + 1, column=8, value=f"=SUM(H2:H{last})")
    tot.font, tot.number_format = Font(bold=True), "#,##0.00"
    if detail.note:
        sh.cell(row=last + 3, column=1, value=detail.note).font = Font(italic=True, size=9)
    for col, w in zip("ABCDEFGHIJK", (6, 11, 13, 13, 34, 32, 26, 13, 7, 90, 34)):
        sh.column_dimensions[col].width = w
    sh.row_dimensions[1].height = 30
    sh.freeze_panes = "A2"
    report.detail_sheet = name
    return report
