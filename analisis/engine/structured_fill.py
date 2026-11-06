"""Llenado dentro de la estructura del papel de trabajo: cada transacción en su propia tabla, columna por columna.

Regla del cliente (guía «Prueba de Ingresos PT A-11»): *cada plantilla lleva sus columnas con su nombre; ahí se
pegan los datos de cada transacción sustituyendo los ejemplos; en «Observaciones» va el análisis del sistema
por transacción; los demás resultados van en hojas aparte del mismo libro.*

Cómo se hace:
- se reconoce la tabla de detalle del papel: una fila de encabezados con un **monto** y al menos dos columnas
  de datos más (fecha, documento, cliente/proveedor, banco, boleta…), y debajo una fila **TOTAL** con
  ``=SUM(...)`` sobre el monto;
- cada columna del papel se empareja por su **nombre** con una columna del archivo subido (sinónimos:
  «Monto Doc.» ↔ «Total_Facturado», «Boleta No.» ↔ «Referencia_Bancaria», «Banco» ↔ «Cuenta_Bancaria_Destino»…);
- si hay más transacciones que filas, la tabla **crece**: se insertan filas antes de la última fila de detalle
  (como en Excel), el ``=SUM`` del total se agranda solo y lo que está debajo (atributos, control interno,
  conclusión, firmas) baja con sus fórmulas, combinadas y formatos (ver ``sheet_rows``);
- las columnas que son del auditor (fecha y monto del depósito, atributos ✓/✗) quedan vacías, y la fórmula
  que dependa de ellas (p. ej. Diferencia = J − F) se condiciona para que no muestre diferencias falsas;
- se completan los parámetros de la prueba (período, población, muestra, método y cuentas revisadas);
- la conclusión de ejemplo de la plantilla se sustituye por la propuesta (pendiente de revisión del auditor;
  el texto original queda en un comentario) y los «✓ Cumple» de ejemplo del control interno pasan a «Por evaluar».

Una fórmula del papel nunca se pierde: se desplaza con sus filas, y la copia se verifica contra el original.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from openpyxl.cell.cell import MergedCell
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .normalize import parse_amount, parse_date
from .shared import Fig, Table, plain
from .sheet_rows import ShiftError, copy_row_format, insert_rows

DETAIL_SHEET = "Detalle integración"
ANALYSIS_SHEET = "ANÁLISIS AGENTES"
COMMENT_AUTHOR = "Audita Análisis"
BLUE = "FF1D4FBE"
MAX_TABLE_ROWS = 5000  # más que esto: integración mensual + hoja de detalle
NO_ALERT = "Sin alertas en las pruebas del sistema"


def norm(text) -> str:
    """Encabezado comparable: sin acentos, minúsculas, sin moneda ni signos («Monto Doc. (Q)» → «monto doc»)."""
    s = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\((q|\$|l|lps?|usd|gtq|hnl|cop|mxn)\)", " ", s)
    s = re.sub(r"[_\n\r\t/]", " ", s)
    s = re.sub(r"[.:()\[\]°º*]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if re.fullmatch(r"(\w ){3,}\w", s):  # «A T R I B U T O S»
        s = s.replace(" ", "")
    return s


# rol de cada columna del PAPEL (en orden: el primero que coincide)
TPL_ROLES: list[tuple[str, re.Pattern]] = [(k, re.compile(p)) for k, p in [
    ("atributo", r"^atribut|^cumpl"),
    ("observaciones", r"^observ|^comentario|^notas?\b|^analisis"),
    ("diferencia", r"^diferencia|^variaci"),
    ("marca", r"^marca|^tilde|^verificad"),
    ("fecha_dep", r"^fecha.*\b(dep|deposito|cobro|pago|banco|acredit)"),
    ("monto_dep", r"^(monto|importe|valor)\b.*\b(dep|deposito|cobr\w*|banco|acredit\w*)\b|^deposit"),
    ("fecha", r"^fecha"),
    ("tipo_doc", r"^(tipo|clase)( de)?( doc\w*| comprobante| documento)?$"),
    ("tipo_otro", r"^tipo|^clase"),  # «Tipo Contrato», «Tipo Inversión»…: no es el tipo de documento
    ("doc_del", r"^del( no| n| num\w*)?$"),
    ("doc_al", r"^al( no| n| num\w*)?$"),
    ("referencia", r"boleta|referencia|^no dep|transferencia|autorizaci"),
    ("documento", r"^(no|n|num|numero|nro) ?(de )?(doc\w*|factura|cheque|comprobante|recibo|partida|poliza|transf\w*|oc|orden\w*|pedido)\b"
                  r"|^orden de (compra|pago)|^oc\b"
                  r"|^(documento|factura|cheque|comprobante|recibo|poliza|partida)( no| n| num\w*)?$|^serie"),
    ("banco", r"^banco|cuenta banc|entidad banc"),
    ("nit", r"^nit\b|^rfc\b|^ruc\b|identificaci"),
    ("cuenta", r"^cuenta|^cta\b|codigo contable|^nombre de (la )?cuenta"),
    ("tercero", r"client|proveedor|beneficiari|tercero|^nombre|razon social|deudor|acreedor"),
    ("descripcion", r"descrip|concepto|detalle|glosa|^motivo"),
    ("categoria", r"categor|rubro|clasificaci"),
    ("subtotal", r"^sub ?total|base imponible"),
    ("iva", r"^iva\b|impuesto"),
    ("estado", r"^estado|^situaci"),
    ("metodo", r"metodo|forma de (pago|cobro)|medio de (pago|cobro)"),
    ("monto", r"^(monto|importe|valor|total|saldo|debe|haber)\b"),  # «Cargo» no: en muchos papeles es el puesto
    ("num", r"^(no|n|nro|#|item|correlativo|num)$"),
]]

# rol de cada columna del ARCHIVO subido (en orden de prioridad; cada columna se usa una sola vez)
SRC_ROLES: list[tuple[str, list[re.Pattern]]] = [(k, [re.compile(p) for p in ps]) for k, ps in [
    ("fecha_dep", [r"fecha.*\b(dep\w*|cobro|pago|acredit\w*)\b"]),
    ("fecha", [r"^fecha$", r"^fecha\b"]),
    ("monto_dep", [r"(monto|importe)\b.*\b(deposit\w*|cobrad\w*)\b", r"^deposit"]),
    ("subtotal", [r"^sub ?total", r"base imponible"]),
    ("iva", [r"^iva\b", r"impuesto"]),
    ("monto", [r"total factur", r"^total\b", r"^monto\b", r"importe", r"^valor\b", r"\btotal\b", r"monto", r"cargo|debe|haber"]),
    ("referencia", [r"referencia", r"boleta", r"transfer", r"autorizaci"]),
    ("banco", [r"^banco\b", r"cuenta banc", r"cuenta (destino|deposit\w*)", r"banco"]),
    ("documento", [r"factura", r"^(no|num|numero|nro) doc|documento|^doc\b", r"cheque", r"comprobante|poliza|partida",
                   r"orden de (compra|pago)|^(no|num|numero|nro) (oc|orden)\b|^oc\b|pedido",
                   r"^(no|num|numero|nro)\b|folio|serie", r"recibo"]),
    ("recibo", [r"recibo"]),
    ("tipo_doc", [r"^tipo\b", r"^clase"]),
    ("nit", [r"^nit\b", r"\brfc\b|\bruc\b|identificaci"]),
    ("tercero", [r"client", r"proveedor|beneficiari", r"tercero|razon social|^nombre"]),
    ("categoria", [r"categor", r"rubro|clasificaci"]),
    ("cuenta", [r"cuenta contable|codigo cuenta|^cta\b", r"^cuenta\b"]),
    ("descripcion", [r"descrip", r"concepto|detalle|glosa|motivo"]),
    ("estado", [r"^estado", r"situaci"]),
    ("metodo", [r"metodo", r"forma de (pago|cobro)|medio de (pago|cobro)"]),
]]

DATA_ROLES = {"fecha", "documento", "doc_del", "doc_al", "tercero", "descripcion", "banco", "referencia", "tipo_doc",
              "cuenta", "nit", "categoria", "subtotal", "iva", "estado", "metodo"}
AUDITOR_ROLES = {"fecha_dep", "monto_dep", "atributo"}  # se dejan para el auditor si el archivo no los trae
DOC_KIND = [("factura", "Factura"), ("cheque", "Cheque"), ("recibo", "Recibo"), ("comprobante", "Comprobante"),
            ("poliza", "Póliza"), ("partida", "Partida"), ("transfer", "Transferencia")]

_RX_TOTAL = re.compile(r"^\s*total", re.I)
_RX_LEDGER = re.compile(r"registros contables|seg[uú]n (el )?mayor|seg[uú]n libros|saldo seg[uú]n (contabilidad|registros)", re.I)
_RX_OBS = re.compile(r"^\s*observaciones generales", re.I)
_RX_CONCL = re.compile(r"^\s*conclusi[oó]n", re.I)
_RX_INTEGRATION = re.compile(r"integraci[oó]n", re.I)
_RX_RESULT_HEAD = re.compile(r"^\s*resultado\s*$", re.I)
_RX_EXAMPLE_OK = re.compile(r"^\s*[✓✔]?\s*cumple\s*$", re.I)
PARAMS = [
    ("periodo", re.compile(r"per[ií]odo (auditado|revisado|examinado|de la prueba|sujeto)|^per[ií]odo\s*:", re.I)),
    ("poblacion", re.compile(r"poblaci[oó]n", re.I)),
    ("muestra", re.compile(r"tama[nñ]o de (la )?muestra|^muestra\b", re.I)),
    ("metodo", re.compile(r"m[eé]todo de (muestreo|selecci[oó]n)", re.I)),
    ("cuentas", re.compile(r"cuentas? (contables? |bancarias? )?(revisadas?|examinadas?|auditadas?)", re.I)),
]


@dataclass
class DetailTable:
    sheet: str
    header_row: int
    header_bottom: int
    total_row: int
    columns: dict[int, tuple[str, str]]  # columna -> (rol, encabezado)
    first_col: int
    last_col: int
    money_col: int
    growable: bool

    @property
    def slots(self) -> list[int]:
        return list(range(self.header_bottom + 1, self.total_row))

    def col(self, role: str) -> int | None:
        return next((c for c, (r, _) in sorted(self.columns.items()) if r == role), None)

    def cols(self, role: str) -> list[int]:
        return [c for c, (r, _) in sorted(self.columns.items()) if r == role]


@dataclass
class StructureReport:
    detail: DetailTable | None = None
    mode: str = ""  # partidas | mensual | ""
    rows_written: int = 0
    inserted: int = 0
    shift: tuple | None = None  # (hoja, fila, cantidad) de las filas insertadas
    guarded: set = field(default_factory=set)  # (hoja, celda) con fórmula condicionada
    regions: list[tuple] = field(default_factory=list)  # (hoja, fila, col, alto, ancho) que se pueden modificar
    figures: list[tuple[str, str, Fig]] = field(default_factory=list)  # (hoja, celda, cifra)
    mapping: list[tuple[str, str]] = field(default_factory=list)  # (columna del papel, origen)
    params: dict = field(default_factory=dict)
    ledger_cell: str = ""
    observations_cell: str = ""
    conclusion_cell: str = ""
    detail_sheet: str = ""
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict:
        d = self.detail
        last = (d.total_row - 1 + self.inserted) if d else 0
        return {
            "tabla": f"{d.sheet}!{get_column_letter(d.first_col)}{d.header_bottom + 1}:{get_column_letter(d.last_col)}{last}" if d else "",
            "modo": self.mode, "filas": self.rows_written, "insertadas": self.inserted, "cuadre": self.ledger_cell,
            "observaciones": self.observations_cell, "conclusion": self.conclusion_cell, "hoja_detalle": self.detail_sheet,
            "columnas": [f"{a} ← {b}" for a, b in self.mapping], "parametros": self.params,
        }


def _text(cell) -> str:
    v = cell.value
    return re.sub(r"\s+", " ", v).strip() if isinstance(v, str) and cell.data_type != "f" else ""


def _writable(ws, row: int, col: int) -> bool:
    cell = ws.cell(row=row, column=col)
    return not isinstance(cell, MergedCell) and cell.data_type != "f"


def _merged_at(ws, row: int, col: int):
    for rng in ws.merged_cells.ranges:
        if rng.min_row <= row <= rng.max_row and rng.min_col <= col <= rng.max_col:
            return rng
    return None


def _tpl_role(text: str) -> str:
    n = norm(text)
    if not n or len(n) > 40:
        return ""
    for role, rx in TPL_ROLES:
        if rx.search(n):
            return role
    return ""


def find_detail_table(ws, max_scan: int = 300) -> DetailTable | None:
    for r in range(1, min(ws.max_row, max_scan) + 1):
        cols: dict[int, tuple[str, str]] = {}
        for c in range(1, min(ws.max_column, 40) + 1):
            text = _text(ws.cell(row=r, column=c))
            role = _tpl_role(text)
            if role and (role != "monto" or "monto" not in {x for x, _ in cols.values()}):
                cols[c] = (role, text)
        roles = {x for x, _ in cols.values()}
        # tabla de transacciones: un monto, una fecha o un número de documento, y al menos dos columnas de datos
        if "monto" not in roles or len(roles & DATA_ROLES) < 2 or not roles & {"fecha", "documento", "doc_del"}:
            continue
        money = next(c for c, (x, _) in cols.items() if x == "monto")
        # el encabezado puede ocupar dos filas (combinadas o subencabezados como «1 … 10» de los atributos)
        bottom = r
        for c in range(1, min(ws.max_column, 40) + 1):
            rng = _merged_at(ws, r, c)
            if rng and rng.min_row == r:
                bottom = max(bottom, rng.max_row)
                for k in range(rng.min_col, rng.max_col + 1):  # un encabezado combinado sobre varias columnas
                    if c in cols and k not in cols:
                        cols[k] = cols[c]
        # subencabezado sin combinar (p. ej. «1 … 10» bajo «A T R I B U T O S»): sin fecha ni monto, con algo escrito
        nxt = bottom + 1
        filled = [c for c in range(1, min(ws.max_column, 40) + 1) if ws.cell(row=nxt, column=c).value not in (None, "")]
        if filled and all(c not in cols or cols[c][0] == "atributo" for c in filled) and any(c in cols for c in filled):
            bottom = nxt
        letter = get_column_letter(money)

        def build(end: int, growable: bool) -> DetailTable:
            # columna de numeración sin encabezado (1, 2, 3… en las filas de ejemplo)
            for c in range(1, min(cols)):
                vals = [ws.cell(row=s, column=c).value for s in range(bottom + 1, min(bottom + 4, end))]
                if vals and all(isinstance(v, (int, float)) for v in vals) and list(vals) == list(range(1, len(vals) + 1)):
                    cols[c] = ("num", "No.")
            # la tabla llega hasta el último encabezado escrito (también los que no tienen rol: son del auditor)
            last = max(max(cols), max((c for c in range(1, min(ws.max_column, 40) + 1) if _text(ws.cell(row=r, column=c))), default=0))
            for c in range(last + 1, min(ws.max_column, 40) + 1):  # observaciones combinadas hacia la derecha
                rng = _merged_at(ws, r, c)
                if rng and rng.min_col <= last:
                    last = c
            return DetailTable(ws.title, r, bottom, end, dict(sorted(cols.items())), min(cols), last, money, growable)

        span = range(min(cols), max(cols) + 1)
        for t in range(bottom + 1, min(bottom + 400, ws.max_row + 1) + 1):
            row_text = " ".join(_text(ws.cell(row=t, column=c)) for c in range(1, money))
            total = ws.cell(row=t, column=money)
            is_sum = total.data_type == "f" and "SUM" in str(total.value).upper()
            if _RX_TOTAL.search(row_text) or is_sum:
                if not (is_sum and letter in str(total.value).upper() and t - bottom > 1):
                    break
                m = re.search(rf"SUM\(\$?{letter}\$?(\d+):\$?{letter}\$?(\d+)\)", str(total.value).upper())
                return build(t, bool(m and int(m.group(1)) <= bottom + 1 and int(m.group(2)) == t - 1))
            # tabla de muestra sin fila TOTAL (p. ej. Auditoría Interna): termina en la primera fila vacía;
            # crecer funciona igual (los rangos como COUNTA(A15:A24) llegan hasta la última fila de ejemplo)
            if t - bottom > 1 and all(ws.cell(row=t, column=c).value in (None, "") for c in span):
                # filas vacías de ejemplo antes de un TOTAL: la tabla sigue hasta el TOTAL
                nxt_row = next((k for k in range(t + 1, min(t + 60, ws.max_row) + 1)
                                if any(ws.cell(row=k, column=c).value not in (None, "") for c in span)), None)
                if nxt_row is not None:
                    nxt_text = " ".join(_text(ws.cell(row=nxt_row, column=c)) for c in range(1, money))
                    nxt_total = ws.cell(row=nxt_row, column=money)
                    if _RX_TOTAL.search(nxt_text) or (nxt_total.data_type == "f" and "SUM" in str(nxt_total.value).upper()):
                        continue
                example = range(bottom + 1, t)
                if any(ws.cell(row=s, column=money).value not in (None, "") for s in example):
                    return build(t, True)
                break
    return None


def map_source(dt: DetailTable, headers: list[str]) -> tuple[dict[str, int], dict[int, tuple[str, object]]]:
    """Empareja las columnas del papel con las del archivo por nombre. Devuelve (rol→índice en archivo, plan por columna)."""
    names = [norm(h) for h in headers]
    used: set[int] = set()
    src: dict[str, int] = {}
    for role, patterns in SRC_ROLES:
        for rx in patterns:
            i = next((k for k, h in enumerate(names) if k not in used and h and rx.search(h)), None)
            if i is not None:
                src[role] = i
                used.add(i)
                break
    plan: dict[int, tuple[str, object]] = {}
    doc_header = names[src["documento"]] if "documento" in src else ""
    seen: set[str] = set()
    for c, (role, header) in dt.columns.items():
        if role in seen and role != "atributo":
            plan[c] = ("clear", None)  # encabezado combinado sobre varias columnas: el dato va solo en la primera
            continue
        seen.add(role)
        same = next((k for k, h in enumerate(names) if h and h == norm(header)), None)
        if same is not None and role not in ("fecha", "monto", "num", "observaciones", "marca", "diferencia"):
            plan[c] = ("src", same)  # la columna del archivo se llama igual que la del papel: esa es
        elif role in ("doc_del", "doc_al", "documento") and "documento" in src:
            plan[c] = ("src", src["documento"])
        elif role == "tipo_doc":
            if "tipo_doc" in src:
                plan[c] = ("src", src["tipo_doc"])
            else:
                kind = next((label for key, label in DOC_KIND if key in doc_header), None)
                plan[c] = ("const", kind) if kind else ("clear", None)
        elif role == "descripcion":
            alt = src.get("descripcion", src.get("categoria"))
            # el papel no tiene columna de proveedor/cliente ni de documento: la descripción los lleva
            who = src.get("tercero") if dt.col("tercero") is None else None
            doc = src.get("documento") if not any(r in ("documento", "doc_del") for r, _ in dt.columns.values()) else None
            if who is not None or doc is not None:
                plan[c] = ("desc", (alt, who, doc))
            else:
                plan[c] = ("src", alt) if alt is not None else ("clear", None)
        elif role in ("fecha", "monto", "num", "observaciones", "marca"):
            plan[c] = (role, None)
        elif role in src:
            plan[c] = ("src", src[role])
        elif role == "diferencia":
            plan[c] = ("keep", None)
        else:
            plan[c] = ("clear", None)  # del auditor (atributos, depósito) o sin dato en el archivo
    return src, plan


def match_score(dt: DetailTable, headers: list[str]) -> int:
    """Cuántas columnas de datos del papel se llenan con este archivo (para elegir el archivo correcto)."""
    src, plan = map_source(dt, headers)
    data = sum(1 for c, (kind, _) in plan.items() if kind in ("src", "const") and dt.columns[c][0] in DATA_ROLES)
    # desempate: la misma palabra en los dos nombres («Proveedor» ↔ «Proveedor (beneficiario)» antes que ↔ «Cliente»)
    words = 0
    for c, (kind, ref) in plan.items():
        if kind == "src" and isinstance(ref, int) and ref < len(headers):
            a = {w for w in norm(dt.columns[c][1]).split() if len(w) >= 4}
            b = {w for w in norm(headers[ref]).split() if len(w) >= 4}
            words += 1 if a & b else 0
    return data + (1 if "fecha" in src else 0) + (2 if "monto" in src else 0) + words


def template_table(path) -> DetailTable | None:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(path, read_only=False)
    except Exception:  # noqa: BLE001
        return None
    try:
        for ws in wb.worksheets:
            dt = find_detail_table(ws)
            if dt:
                return dt
    finally:
        wb.close()
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


def _band_models(ws, dt: DetailTable, examples: list[int], first: int) -> dict[int, int]:
    """Fila modelo para las filas impares y pares de la tabla: el formato más común entre las filas de ejemplo."""
    from collections import Counter

    def sig(r):
        out = []
        for c in dt.columns:
            f = ws.cell(row=r, column=c).fill
            out.append(f.fgColor.rgb if f is not None and f.patternType == "solid" else None)
        return tuple(out)

    models: dict[int, int] = {}
    for parity in (0, 1):
        rows = [r for r in examples if (r - first) % 2 == parity]
        if rows:
            common = Counter(sig(r) for r in rows).most_common(1)[0][0]
            models[parity] = next(r for r in rows if sig(r) == common)
    if not models:
        models = {0: first}
    models.setdefault(0, models.get(1))
    models.setdefault(1, models[0])
    return models


def _col_width(ws, col: int) -> float:
    dim = next((d for d in ws.column_dimensions.values() if d.min and d.max and d.min <= col <= d.max), None)
    return dim.width if dim and dim.width else 9.14


def _display_len(v) -> int:
    if v is None:
        return 0
    if isinstance(v, (date, datetime)):
        return 10
    if isinstance(v, float):
        return len(f"{v:,.2f}")
    return len(str(v))


def _fit_data_column(ws, col: int, rows: list[int], cap: float = 40) -> None:
    """Ensancha una columna de datos para que el dato pegado se lea completo (solo formato)."""
    from .sheet_rows import set_column_width

    longest = max((_display_len(ws.cell(row=r, column=col).value) for r in rows), default=0)
    width = _col_width(ws, col)
    if longest + 1 > width:
        set_column_width(ws, col, min(longest * 1.05 + 2, cap))


def _fit_text_column(ws, col: int, rows: list[int], cap: float = 80) -> None:
    """La columna de Observaciones se ensancha para que el análisis se lea en Excel (solo formato: ancho y alto)."""
    from .sheet_rows import set_column_width

    width = _col_width(ws, col)
    longest = max((len(str(ws.cell(row=r, column=col).value or "")) for r in rows), default=0)
    if longest > width:
        width = min(max(width, longest * 0.95 + 2), cap)
        set_column_width(ws, col, width)
    per_line = max(width * 1.1, 10)
    for r in rows:
        cell = ws.cell(row=r, column=col)
        text = str(cell.value or "")
        if not text:
            continue
        cell.alignment = Alignment(wrap_text=True, vertical=cell.alignment.vertical or "center",
                                   horizontal=cell.alignment.horizontal)
        lines = -(-len(text) // int(per_line))
        if lines > 1:
            ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 15, lines * 12.75 + 2)


def is_integration_paper(ws, dt: DetailTable) -> bool:
    for r in range(1, dt.header_row):
        for c in range(1, min(ws.max_column, 15) + 1):
            if _RX_INTEGRATION.search(_text(ws.cell(row=r, column=c))):
                return True
    return False


def _comment(cell, text: str, height: int = 90, width: int = 300) -> None:
    cell.comment = Comment(text, COMMENT_AUTHOR, height=height, width=width)


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
        _comment(cell, f"{fig.fid or 'Cifra'} · Origen: {fig.origin()}" + (f"\n{note}" if note else ""), 70, 260)


def _value(raw, role: str):
    """Valor del archivo listo para la celda (fechas como fecha, importes como número, códigos sin «.0»)."""
    if raw is None or raw == "":
        return None
    if role in ("fecha", "fecha_dep"):
        return parse_date(raw) or raw
    if role in ("subtotal", "iva", "monto_dep", "monto"):
        amount = parse_amount(raw)
        return float(amount) if amount is not None else raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, Decimal):
        return float(raw)
    return str(raw).strip() if not isinstance(raw, (int, float, date, datetime)) else raw


_RX_SAME_ROW_REF = re.compile(r"(?<![A-Z$])\$?([A-Z]{1,3})\$?(\d+)(?!\d)")


def _guard(formula: str, row: int, blank_cols: set[int]) -> str | None:
    """«=J19-F19» con J del auditor → «=IF(J19="","",J19-F19)»: sin monto de depósito no hay diferencia."""
    from openpyxl.utils import column_index_from_string

    refs = [(m.group(1), int(m.group(2))) for m in _RX_SAME_ROW_REF.finditer(formula.upper())]
    blanks = [f"{col}{r}" for col, r in refs if r == row and column_index_from_string(col) in blank_cols]
    if not blanks or re.match(r'^=IF\(\$?[A-Z]{1,3}\$?\d+="",""', formula.upper()):
        return None  # sin dependencia del auditor, o ya condicionada
    return f'=IF({blanks[0]}="","",{formula[1:]})'


def _param_target(ws, row: int, col: int) -> int | None:
    """Celda de valor a la derecha de una etiqueta («Población:» → la celda de la cifra)."""
    rng = _merged_at(ws, row, col)
    c = (rng.max_col if rng else col) + 1
    while c <= min(ws.max_column, 40):
        cell = ws.cell(row=row, column=c)
        if isinstance(cell, MergedCell):
            c += 1
            continue
        if cell.data_type == "f":
            return None
        text = _text(cell)
        if text.endswith(":") and len(text) > 3:
            return None  # otra etiqueta: la fila no tiene celda de valor
        return c
    return None


def _fill_params(ws, dt: DetailTable, report: StructureReport, values: dict) -> None:
    for r in range(1, dt.header_row):
        for c in range(1, min(ws.max_column, 40) + 1):
            text = _text(ws.cell(row=r, column=c))
            # solo etiquetas («Población (total documentos):»), no frases como «Muestra: 10 órdenes de compra…»
            if not text or len(text) > 45 or not text.rstrip().endswith(":"):
                continue
            for key, rx in PARAMS:
                if key in report.params or not rx.search(text) or values.get(key) in (None, ""):
                    continue
                target = _param_target(ws, r, c)
                if not target:
                    continue
                cell = ws.cell(row=r, column=target)
                before = cell.value
                cell.value = values[key]
                if isinstance(values[key], int):
                    cell.number_format = "#,##0"
                cell.alignment = Alignment(horizontal="left", vertical=cell.alignment.vertical, wrap_text=cell.alignment.wrap_text)
                note = "Completado por Audita Análisis con los datos del archivo analizado."
                if before not in (None, ""):
                    note += f"\nValor de ejemplo de la plantilla: {before}"
                _comment(cell, note, 70, 260)
                report.params[key] = f"{ws.title}!{get_column_letter(target)}{r}"
                report.regions.append((ws.title, r, target, 1, 1))
                break


def fill_structure(wb, *, detail: Table | None, monthly: Table | None, ledger_total: Decimal | None,
                   observations: list[str], conclusion: str, results_anchor: str,
                   source: Table | None = None, source_name: str = "", prefer_sheet: str | None = None) -> StructureReport:
    """``prefer_sheet``: la hoja que eligió el auditor; si tiene tabla de transacciones, los datos van ahí."""
    report = StructureReport()
    if detail is None or not detail.rows:
        return report
    headers = [str(h) for h in (source.head[1:] if source else [])]
    ws = dt = None
    best = 0
    for sheet in wb.worksheets:
        found = find_detail_table(sheet)
        if not found:
            continue
        score = match_score(found, headers) if headers else (4 if is_integration_paper(sheet, found) else 0)
        if prefer_sheet and sheet.title == prefer_sheet and score >= 4:
            score += 1000  # la elección del auditor manda
        if score > best:
            ws, dt, best = sheet, found, score
    if ws is None or best < 4:
        return report
    src, plan = map_source(dt, headers) if headers else ({}, {c: (r if r in ("fecha", "monto", "num", "observaciones", "marca") else "clear", None) for c, (r, _) in dt.columns.items()})
    if not headers:  # sin archivo de origen detallado: columnas por el formato de la tabla de integración
        legacy = {"tipo_doc": 2, "documento": 3, "tercero": 4, "descripcion": 5, "cuenta": 6}
        for c, (role, _) in dt.columns.items():
            if role in legacy:
                plan[c] = ("legacy", legacy[role])
    raw_by_row = {int(r[0]): r[1:] for r in source.rows} if source else {}
    items = detail.rows
    total_items = len(items) + detail.truncated
    slots = dt.slots

    if total_items > len(slots) and not (dt.growable and total_items <= MAX_TABLE_ROWS and not detail.truncated):
        fits_months = monthly is not None and 0 < len(monthly.rows) <= len(slots) and is_integration_paper(ws, dt)
        if not fits_months:
            report.warnings.append(
                f"La tabla de {ws.title} tiene {len(slots)} filas y hay {total_items:,} transacciones; su total no es un "
                f"=SUM continuo que pueda crecer: no se llenó la tabla del papel (los resultados van en hoja aparte)."
            )
            return report
        return _fill_monthly(wb, ws, dt, report, detail, monthly, ledger_total, observations, conclusion, results_anchor)

    report.detail = dt
    report.mode = "partidas"
    max_col = max(ws.max_column, dt.last_col)
    # 1) la tabla crece si hace falta (antes de la última fila de detalle, como en Excel)
    if total_items > len(slots):
        n = total_items - len(slots)
        idx = slots[-1]
        try:
            insert_rows(wb, ws, idx, n)
        except ShiftError as exc:
            report.detail, report.mode = None, ""
            report.warnings.append(f"No se pudo ampliar la tabla de {ws.title}: {exc} Los resultados van en hoja aparte.")
            return report
        examples = [s for s in slots if s < idx] + [s + n for s in slots if s >= idx]
        models = _band_models(ws, dt, examples, slots[0])
        for r in range(idx, idx + n):
            copy_row_format(ws, models[(r - slots[0]) % 2], r, max_col)
        report.inserted, report.shift = n, (ws.title, idx, n)
        slots = list(range(slots[0], slots[-1] + n + 1))
        dt_total = dt.total_row + n
    else:
        examples = list(slots)
        models = _band_models(ws, dt, examples, slots[0])
        dt_total = dt.total_row
    # las filas de ejemplo traían colores propios de sus datos de ejemplo (p. ej. una diferencia en rosa):
    # toda la tabla queda con el formato normal de la plantilla, en franjas (solo formato; valores y fórmulas no)
    for r in examples:
        if r not in models.values():
            copy_row_format(ws, models[(r - slots[0]) % 2], r, max_col, formulas=False)

    # 2) columnas del auditor que quedan vacías → las fórmulas que dependen de ellas se condicionan
    # (las del auditor, las que el archivo no trae y las de encabezado sin rol, p. ej. «¿Tiene 3 cotizaciones?»)
    span = range(dt.first_col, dt.last_col + 1)
    blank_cols = {c for c in span if c not in dt.columns or (plan.get(c, ("",))[0] == "clear" and dt.columns[c][0] != "num")}
    for c, (role, header) in dt.columns.items():
        kind, ref = plan.get(c, ("clear", None))
        if kind in ("fecha", "monto") and kind in src and headers:
            kind, ref = "src", src[kind]
            report.mapping.append((header, headers[ref]))
            _comment(ws.cell(row=dt.header_row, column=c),
                     f"Audita Análisis pegó aquí la columna «{headers[ref]}» de {source_name or 'el archivo analizado'}.", 60, 260)
            continue
        if kind == "src" and ref is not None and headers:
            report.mapping.append((header, headers[ref]))
            _comment(ws.cell(row=dt.header_row, column=c),
                     f"Audita Análisis pegó aquí la columna «{headers[ref]}» de {source_name or 'el archivo analizado'}.", 60, 260)
        elif kind == "const":
            report.mapping.append((header, f"«{ref}» (todas las filas tienen número de {str(ref).lower()})"))
    obs_col = dt.col("observaciones")
    if obs_col:
        report.mapping.append((dt.columns[obs_col][1], "Análisis del sistema por transacción"))
    has_estado_col = any(plan.get(c, ("",))[0] == "src" and dt.columns[c][0] in ("estado", "metodo") for c in dt.columns)

    # 3) una transacción por fila; lo que era ejemplo se sustituye o se limpia
    for i, (slot, row) in enumerate(zip(slots, items), start=1):
        n_, fecha, tipo, numero, proveedor, desc, cuenta, monto, marca, obs = row
        raw = raw_by_row.get(int(n_), [])
        row_blank = set(blank_cols)
        for c in span:
            role = dt.columns.get(c, ("", ""))[0]
            kind, ref = plan.get(c, ("clear", None))
            cell = ws.cell(row=slot, column=c)
            if isinstance(cell, MergedCell):
                continue
            if cell.data_type == "f":
                guarded = _guard(str(cell.value), slot, row_blank) if row_blank else None
                if guarded:
                    cell.value = guarded
                    report.guarded.add((ws.title, cell.coordinate))
                    row_blank.add(c)  # la que depende de esta (p. ej. el semáforo 🟢/🔴) también espera al auditor
                else:
                    row_blank.discard(c)
                continue
            if kind == "num":
                value = i
            elif kind == "fecha":
                value = fecha
            elif kind == "monto":
                fig = monto if isinstance(monto, Fig) else None
                _put(ws, report, slot, c, float(plain(monto)), fig=fig, number="#,##0.00")
                continue
            elif kind == "marca":
                value = marca or None
            elif kind == "observaciones":
                analysis = obs or NO_ALERT
                prefix = "" if has_estado_col else " · ".join(
                    str(_value(raw[src[k]], k)) for k in ("estado", "metodo") if k in src and src[k] < len(raw) and raw[src[k]] not in (None, ""))
                value = f"{prefix} — {analysis}" if prefix else analysis
            elif kind == "src":
                value = _value(raw[ref], role) if ref is not None and ref < len(raw) else None
            elif kind == "desc":
                alt, who, doc = ref
                at = lambda k: _value(raw[k], "texto") if k is not None and k < len(raw) else None  # noqa: E731
                text = " — ".join(str(x) for x in (at(who), at(alt)) if x not in (None, ""))
                value = (text + (f" · Doc. {at(doc)}" if at(doc) not in (None, "") else "")) or None
            elif kind == "legacy":
                value = row[ref] or None
            elif kind == "const":
                value = ref
            elif kind == "keep":
                continue
            else:
                value = None
            cell.value = value
            if isinstance(value, (date, datetime)):
                cell.number_format = "dd/mm/yyyy"
            elif isinstance(value, float) and role in ("subtotal", "iva", "monto_dep"):
                cell.number_format = "#,##0.00"
    report.rows_written = min(len(slots), len(items))
    used_rows = slots[:report.rows_written]
    for c, (role, _) in dt.columns.items():
        if plan.get(c, ("",))[0] in ("src", "const", "desc", "legacy") and role not in ("observaciones",):
            _fit_data_column(ws, c, used_rows, cap=48 if role in ("descripcion", "tercero") else 40)
    if obs_col:
        _fit_text_column(ws, obs_col, used_rows)
    # filas de ejemplo que sobran (menos transacciones que filas): se limpian
    for slot in slots[report.rows_written:]:
        for c in span:
            if _writable(ws, slot, c) and ws.cell(row=slot, column=c).value not in (None, ""):
                ws.cell(row=slot, column=c).value = None
    report.regions.append((ws.title, slots[0], 1, len(slots), max_col))

    # 4) parámetros de la prueba
    dates = [r[1] for r in items if isinstance(r[1], date)]
    accounts: list[str] = []
    for k in ("banco", "cuenta"):
        if k not in src:
            continue
        found_values = set()
        for r in items:
            raw = raw_by_row.get(int(r[0]), [])
            if src[k] < len(raw) and raw[src[k]] not in (None, ""):
                found_values.add(str(_value(raw[src[k]], k)))
        accounts = sorted(found_values)
        if accounts:
            break
    values = {
        "periodo": f"{min(dates):%d/%m/%Y} al {max(dates):%d/%m/%Y}" if dates else None,
        "poblacion": total_items,
        "muestra": total_items,
        "metodo": "100 % de la población (todas las transacciones analizadas por Audita Análisis)",
        "cuentas": (" · ".join(accounts) if len(accounts) <= 4 else f"{len(accounts)} cuentas") if accounts else None,
    }
    _fill_params(ws, dt, report, values)

    _after_table(wb, ws, dt, dt_total, report, ledger_total, observations, conclusion, results_anchor, total_items,
                 detail_sheet=False)
    return report


def _after_table(wb, ws, dt, total_row, report, ledger_total, observations, conclusion, results_anchor, total_items,
                 detail_sheet: bool) -> None:
    # cuadre contra registros contables
    for r in range(total_row + 1, min(total_row + 15, ws.max_row) + 1):
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
    where = f"la hoja «{DETAIL_SHEET}»" if detail_sheet else "la tabla de este papel (columna Observaciones)"
    for r in range(total_row + 1, min(total_row + 40, ws.max_row) + 1):
        if any(_RX_OBS.search(_text(ws.cell(row=r, column=c))) for c in range(1, 4)):
            tr = r + 1
            if _writable(ws, tr, 1) and ws.cell(row=tr, column=1).value in (None, ""):
                lines = observations[:8] + [
                    f"Las {total_items:,} transacciones, con el análisis de cada una, están en {where}; "
                    f"resultados completos de Audita Análisis en {results_anchor} y en la hoja «Evidencia».",
                ]
                cell = ws.cell(row=tr, column=1)
                cell.value = "\n".join(lines)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.font = Font(size=9)
                _fit_rows(ws, tr, lines)
                report.observations_cell = f"{ws.title}!A{tr}"
                report.regions.append((ws.title, tr, 1, 1, 1))
            break

    # control interno: los «✓ Cumple» de ejemplo no se dan por buenos
    for r in range(total_row + 1, min(total_row + 80, ws.max_row) + 1):
        head = next((c for c in range(1, min(ws.max_column, 40) + 1) if _RX_RESULT_HEAD.search(_text(ws.cell(row=r, column=c)))), None)
        if not head:
            continue
        first = True
        for k in range(r + 1, min(r + 40, ws.max_row) + 1):
            cell = ws.cell(row=k, column=head)
            if isinstance(cell, MergedCell) or cell.data_type == "f" or not _RX_EXAMPLE_OK.search(_text(cell)):
                if _text(cell) == "" and k > r + 1 and _text(ws.cell(row=k, column=1)) == "":
                    break
                continue
            cell.value = "Por evaluar"
            if _col_width(ws, head) < 12:
                from .sheet_rows import set_column_width

                set_column_width(ws, head, 12)  # que «Por evaluar» se lea (solo formato)
            if first:
                _comment(cell, "La plantilla traía «✓ Cumple» de ejemplo. Lo evalúa el auditor con base en las pruebas; "
                               "revise las alertas del análisis antes de marcar.", 70, 260)
                first = False
            report.regions.append((ws.title, k, head, 1, 1))
        break

    # conclusión: la de ejemplo de la plantilla se sustituye por la propuesta (el original queda en un comentario)
    for r in range(total_row + 1, min(total_row + 80, ws.max_row) + 1):
        if any(_RX_CONCL.search(_text(ws.cell(row=r, column=c))) for c in range(1, 4)):
            tr = r + 1
            if _writable(ws, tr, 1):
                cell = ws.cell(row=tr, column=1)
                before = cell.value
                cell.value = f"Propuesta de Audita Análisis (pendiente de revisión y firma del auditor): {conclusion}"
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if before not in (None, ""):
                    _comment(cell, "Texto de ejemplo de la plantilla (sustituido):\n" + str(before)[:900], 120, 320)
                    report.warnings.append(
                        f"La conclusión de ejemplo de la plantilla ({ws.title}!A{tr}) se sustituyó por la propuesta del análisis; "
                        "el texto original quedó en un comentario. El auditor la revisa antes de firmar."
                    )
                report.regions.append((ws.title, tr, 1, 1, 1))
                report.conclusion_cell = f"{ws.title}!A{tr}"
            break


def _fill_monthly(wb, ws, dt, report, detail, monthly, ledger_total, observations, conclusion, results_anchor):
    """Más transacciones de las que caben y la tabla no puede crecer: integración mensual + hoja de detalle."""
    report.detail = dt
    report.mode = "mensual"
    slots = dt.slots
    total_items = len(detail.rows) + detail.truncated
    for i, (slot, row) in enumerate(zip(slots, monthly.rows), start=1):
        key, label, count, tipo, cuenta, monto, with_alert, checked, last = row
        for c, (role, _) in dt.columns.items():
            if not _writable(ws, slot, c):
                continue
            if role == "num":
                ws.cell(row=slot, column=c).value = i
            elif role == "tipo_doc":
                ws.cell(row=slot, column=c).value = tipo if tipo and tipo != "Varios" else None
            elif role == "fecha":
                _put(ws, report, slot, c, last, number="dd/mm/yyyy")
            elif role == "descripcion":
                ws.cell(row=slot, column=c).value = f"{label} · {count:,} partidas"
            elif role == "cuenta":
                ws.cell(row=slot, column=c).value = cuenta or None
            elif role == "monto":
                fig = monto if isinstance(monto, Fig) else None
                _put(ws, report, slot, c, float(plain(monto)), fig=fig, number="#,##0.00",
                     note=f"Suma de {count:,} partidas de {label}; detalle en la hoja «{DETAIL_SHEET}».")
            elif role == "marca":
                ws.cell(row=slot, column=c).value = "Σ"
            elif role == "observaciones":
                notes = []
                if with_alert:
                    notes.append(f"{with_alert} alerta{'s' if with_alert != 1 else ''}")
                if checked:
                    notes.append(f"{checked} cotejada{'s' if checked != 1 else ''}")
                ws.cell(row=slot, column=c).value = " · ".join(notes) or None
            else:
                ws.cell(row=slot, column=c).value = None
    report.rows_written = len(monthly.rows)
    for slot in slots[report.rows_written:]:
        for c in dt.columns:
            if _writable(ws, slot, c) and ws.cell(row=slot, column=c).value not in (None, ""):
                ws.cell(row=slot, column=c).value = None
    report.regions.append((ws.title, slots[0], dt.first_col, len(slots), dt.last_col - dt.first_col + 1))
    _after_table(wb, ws, dt, dt.total_row, report, ledger_total, observations, conclusion, results_anchor, total_items,
                 detail_sheet=True)

    name, k = DETAIL_SHEET, 2
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
