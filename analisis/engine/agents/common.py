"""Contexto, columnas y utilidades comunes de los agentes.

Todos los números se calculan aquí con ``Decimal``; ningún agente usa IA para calcular.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..classify import TIPO_CONTRATO
from ..crossmatch import AuxRow, CruceRow
from ..extract import Extraction
from ..normalize import norm_doc, parse_amount, parse_date
from ..readers import Tabular
from ..shared import MAX_FIG_ROWS, Fig, Finding

AGENTES = {
    "masivo": "Datos masivos",
    "predictivo": "Predictivo",
    "fraudes": "Detección de fraudes",
    "contratos": "Revisión de contratos",
}
NIA_AGENTE = {
    "masivo": "NIA 500 · 530",
    "predictivo": "NIA 520 · 315",
    "fraudes": "NIA 240 · 330",
    "contratos": "NIA 500 · 501 · 250",
}

ALTA, MEDIA, BAJA = "Alta", "Media", "Baja"
CAUSA_PENDIENTE = "Por confirmar con la gerencia"


class AgentError(Exception):
    """Falta un dato indispensable; el mensaje se muestra al auditor."""


@dataclass
class ColumnMap:
    group: int = 0
    amount: int = -1
    doc: int = -1
    date: int = -1


_RX_GROUP = re.compile(r"prov|cuenta|client|nombre|contrat", re.I)
_RX_AMOUNT = re.compile(r"import|monto|valor|total|saldo", re.I)
_RX_NOT_AMOUNT = re.compile(r"sub.?total|\biva\b|impuesto|descuento|retenci", re.I)
_RX_DOC = re.compile(r"factura|n[uú]m|docu|serie|^no\.?$|^n[°º]", re.I)
_RX_DATE = re.compile(r"fecha", re.I)
_RX_DATE_CONTRACT = re.compile(r"venc|fin|hasta|fecha", re.I)


def _first(headers: list[str], rx: re.Pattern) -> int:
    for i, h in enumerate(headers):
        if rx.search(h):
            return i
    return -1


def detect_columns(headers: list[str], agent: str = "masivo") -> ColumnMap:
    """Propone columnas por el encabezado (guía §5); el auditor puede cambiarlas."""
    group = _first(headers, _RX_GROUP)
    # el importe es el total (no el subtotal, el IVA ni un descuento)
    amount = next((i for i, h in enumerate(headers) if _RX_AMOUNT.search(h) and not _RX_NOT_AMOUNT.search(h)), -1)
    if amount < 0:
        amount = _first(headers, _RX_AMOUNT)
    return ColumnMap(
        group=group if group >= 0 else 0,
        amount=amount if amount >= 0 else len(headers) - 1,
        doc=_first(headers, _RX_DOC),
        date=_first(headers, _RX_DATE_CONTRACT if agent == "contratos" else _RX_DATE),
    )


def resolve_columns(headers: list[str], overrides: dict | None, agent: str) -> ColumnMap:
    """Detección automática con correcciones del auditor (nombre de encabezado o índice)."""
    cols = detect_columns(headers, agent)
    for key in ("group", "amount", "doc", "date"):
        wanted = (overrides or {}).get(key)
        if wanted in (None, ""):
            continue
        if isinstance(wanted, int) and -1 <= wanted < len(headers):
            setattr(cols, key, wanted)
        elif isinstance(wanted, str) and wanted in headers:
            setattr(cols, key, headers.index(wanted))
        elif isinstance(wanted, str) and wanted.isdigit() and int(wanted) < len(headers):
            setattr(cols, key, int(wanted))
    return cols


def build_aux_rows(tab: Tabular, cols: ColumnMap) -> list[AuxRow]:
    out = []
    for row in tab.rows:
        v = row.values

        def at(i):
            return v[i] if 0 <= i < len(v) else None

        group = at(cols.group)
        doc_raw = at(cols.doc)
        out.append(
            AuxRow(
                n=row.n,
                group=str(group).strip() if group is not None else "",
                amount=parse_amount(at(cols.amount)),
                doc=norm_doc(doc_raw),
                doc_raw="" if doc_raw is None else (str(int(doc_raw)) if isinstance(doc_raw, float) and doc_raw.is_integer() else str(doc_raw)),
                date=parse_date(at(cols.date)) if cols.date >= 0 else None,
                values=v,
            )
        )
    return out


@dataclass
class DocSection:
    """Una página o sección ya clasificada y extraída."""

    doc: str
    page: int
    tipo: str
    confianza: float
    metodo: str
    text: str
    extraction: Extraction | None = None
    path: str = ""
    bboxes: dict[str, dict] = field(default_factory=dict)  # campo -> rectángulo en la página (PDF)


@dataclass
class AuxSet:
    """Otra tabla del expediente (para cruzar gasto contra contratos)."""

    name: str
    sheet: str
    headers: list[str]
    cols: ColumnMap
    rows: list[AuxRow]


@dataclass
class AgentContext:
    source_name: str
    sheet: str
    headers: list[str]
    cols: ColumnMap
    rows: list[AuxRow]
    params: dict = field(default_factory=dict)
    sections: list[DocSection] = field(default_factory=list)
    cruce: list[CruceRow] = field(default_factory=list)
    aux_sets: list[AuxSet] = field(default_factory=list)

    @property
    def group_header(self) -> str:
        return self.headers[self.cols.group] if 0 <= self.cols.group < len(self.headers) else "Grupo"

    @property
    def contracts(self) -> list[DocSection]:
        return [s for s in self.sections if s.tipo == TIPO_CONTRATO]

    def param_decimal(self, key: str, default: str) -> Decimal:
        value = self.params.get(key)
        parsed = parse_amount(value) if value not in (None, "") else None
        return parsed if parsed is not None else Decimal(default)

    def param_float(self, key: str, default: float) -> float:
        value = self.params.get(key)
        parsed = parse_amount(value) if value not in (None, "") else None
        return float(parsed) if parsed is not None else default

    def param_date(self, key: str) -> date | None:
        return parse_date(self.params.get(key))

    # ------------------------------------------------------------------ cifras
    def fig_row(self, row: AuxRow, value=None, label: str = "") -> Fig:
        return Fig(
            value=row.amount if value is None else value,
            doc=self.source_name,
            sheet=self.sheet,
            rows=[row.n],
            label=label,
            col=self.cols.amount,
        )

    def fig_sum(self, rows: list[AuxRow], value: Decimal, label: str = "", extra: dict | None = None) -> Fig:
        numbers = [r.n for r in rows]
        agg = {
            "op": "sum",
            "amount_col": self.cols.amount,
            "count": len(rows),
            **(extra or {}),
        }
        return Fig(
            value=value,
            doc=self.source_name,
            sheet=self.sheet,
            rows=numbers if len(numbers) <= MAX_FIG_ROWS else [],
            agg=agg if len(numbers) > MAX_FIG_ROWS else None,
            label=label,
            col=self.cols.amount,
        )

    def ref_rows(self, rows: list[AuxRow]) -> str:
        nums = [r.n for r in rows]
        if len(nums) == 1:
            return f"{self.source_name} · fila {nums[0]}"
        shown = ", ".join(str(n) for n in nums[:3])
        more = f"… ({len(nums)})" if len(nums) > 3 else ""
        return f"{self.source_name} · filas {shown}{more}"


def finding(agent: str, kind: str, procedimiento: str, resultado: str, alerta: str, **kw) -> Finding:
    return Finding(agent=agent, kind=kind, procedimiento=procedimiento, resultado=resultado, alerta=alerta, **kw)


def sum_amounts(rows: list[AuxRow]) -> Decimal:
    total = Decimal(0)
    for r in rows:
        if r.amount is not None:
            total += r.amount
    return total
