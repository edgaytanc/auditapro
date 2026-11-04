"""Etapa 03 · Cruce de cada factura o comprobante contra el auxiliar elegido.

Orden de búsqueda (guía §6.3):
1. Por número de documento normalizado, si el auxiliar tiene esa columna.
2. Si no aparece, por importe con tolerancia (0.5 % por defecto) y fecha dentro de ±5 días.
3. Si aparece por número, se compara el importe con la misma tolerancia.
"""
from __future__ import annotations

import bisect
import unicodedata
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .normalize import fmt_num, norm_doc

DEFAULT_TOLERANCE = Decimal("0.005")
DEFAULT_DAYS = 5


@dataclass
class AuxRow:
    """Una fila del auxiliar ya interpretada (ver ``agents.common.build_aux_rows``)."""

    n: int
    group: str
    amount: Decimal | None
    doc: str  # número de documento normalizado
    doc_raw: str
    date: date | None
    values: list


@dataclass
class CruceRow:
    numero: str
    proveedor: str
    total: Decimal | None
    estado: str  # cuadra | no_cuadra | falta_soporte
    motivo: str
    doc_name: str
    page: int
    aux_row: int | None = None
    aux_amount: Decimal | None = None
    fig: object | None = None  # ``Fig`` del importe del documento (con página y coordenadas)


def within_tolerance(a: Decimal, b: Decimal, tolerance: Decimal) -> bool:
    return abs(a - b) <= max(Decimal("0.01"), abs(a) * tolerance)


class AuxIndex:
    def __init__(self, rows: list[AuxRow]):
        self.rows = rows
        self.by_doc: dict[str, list[AuxRow]] = {}
        amounts: list[tuple[Decimal, int]] = []
        for i, row in enumerate(rows):
            if row.doc:
                self.by_doc.setdefault(row.doc, []).append(row)
            if row.amount is not None:
                amounts.append((row.amount, i))
        amounts.sort(key=lambda t: t[0])
        self._amounts = amounts
        self._keys = [a for a, _ in amounts]

    def find_by_supplier(self, supplier: str, doc_date: date, days: int) -> AuxRow | None:
        """Partida del mismo proveedor más cercana en fecha (± días); para informar «importe difiere»."""
        best = None
        for row in self.rows:
            if row.date is None or row.amount is None or abs((row.date - doc_date).days) > days:
                continue
            if not same_supplier(row.group, supplier):
                continue
            if best is None or abs((row.date - doc_date).days) < abs((best.date - doc_date).days):
                best = row
        return best

    def find_by_amount(self, amount: Decimal, tolerance: Decimal, doc_date: date | None, days: int) -> AuxRow | None:
        slack = max(Decimal("0.01"), abs(amount) * tolerance)
        lo = bisect.bisect_left(self._keys, amount - slack)
        hi = bisect.bisect_right(self._keys, amount + slack)
        best = None
        for _, idx in self._amounts[lo:hi]:
            row = self.rows[idx]
            if doc_date and row.date and abs((row.date - doc_date).days) > days:
                continue
            if best is None or abs(row.amount - amount) < abs(best.amount - amount):
                best = row
        return best


_STOP = {"sa", "s", "a", "ltda", "cia", "y", "de", "del", "la", "el", "los", "las", "gt", "guatemala", "sociedad", "anonima"}


def _name_tokens(name: str) -> set[str]:
    text = unicodedata.normalize("NFKD", str(name or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return {t for t in re.split(r"[^a-z0-9]+", text) if t and t not in _STOP}


def same_supplier(a: str, b: str) -> bool:
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.75


def match_document(
    index: AuxIndex,
    numero: str,
    total: Decimal | None,
    doc_date: date | None,
    tolerance: Decimal = DEFAULT_TOLERANCE,
    days: int = DEFAULT_DAYS,
    proveedor: str = "",
) -> tuple[str, str, AuxRow | None]:
    """Devuelve (estado, motivo, fila del auxiliar).

    Orden: 1) número de documento; 2) importe (± tolerancia) y fecha (± días); 3) mismo proveedor y fecha
    (± días) con otro importe → «Importe difiere» (no «sin registro»: la partida existe, el monto no coincide).
    """
    row = None
    how = "numero"
    key = norm_doc(numero)
    if key and key in index.by_doc:
        candidates = index.by_doc[key]
        if total is not None:
            candidates = sorted(
                candidates, key=lambda r: abs((r.amount or Decimal(0)) - total) if r.amount is not None else Decimal("1e12")
            )
        row = candidates[0]
    if row is None and total is not None:
        row = index.find_by_amount(total, tolerance, doc_date, days)
        how = "importe"
    if row is None and proveedor and doc_date:
        row = index.find_by_supplier(proveedor, doc_date, days)
        how = "proveedor"
    if row is None:
        return "no_cuadra", "Documento sin registro en el auxiliar", None
    if total is not None and row.amount is not None and not within_tolerance(row.amount, total, tolerance):
        return (
            "no_cuadra",
            f"Importe difiere: documento {fmt_num(total)} vs. auxiliar {fmt_num(row.amount)}",
            row,
        )
    if how == "numero":
        return "cuadra", "Número e importe coinciden", row
    return "cuadra", f"Importe y fecha coinciden (± {days} días)", row


def missing_support(index: AuxIndex, matched: set[int], limit: int = 200) -> list[AuxRow]:
    """Filas del auxiliar sin documento de soporte (opcional, solo dentro de la muestra)."""
    out = []
    for row in index.rows:
        if row.n not in matched:
            out.append(row)
            if len(out) >= limit:
                break
    return out
