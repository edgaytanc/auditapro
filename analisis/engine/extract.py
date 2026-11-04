"""Etapa 02 · Extracción de campos por tipo de documento (reglas base de la guía §6.2)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .classify import (
    TIPO_COMPROBANTE,
    TIPO_CONTRATO,
    TIPO_ESTADO,
    TIPO_FACTURA,
    TIPO_PLANILLA,
)
from .normalize import nit_valido, parse_amount, parse_date

_NUMERO = re.compile(
    r"(?:factura|fact\.|dte|n[uú]mero|n[°º]|no\.)\s*(?:de factura)?\s*[:#]?\s*([A-Z]{0,4}-?\d{3,})", re.I
)
_FECHA = re.compile(r"\b(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
_NIT = re.compile(r"NIT\s*[:.]?\s*([\dKk\-]{4,})", re.I)
_PROVEEDOR = re.compile(r"(proveedor|emisor|raz[oó]n social)\s*:", re.I)
_TOTAL = re.compile(
    r"(total(?:\s+a\s+pagar|\s+factura|\s+general)?|saldo\s+(?:final|al\s+corte)"
    r"|monto\s+(?:total\s+)?del\s+contrato|monto\s+total)\s*:?\s*(?:Q|\$|USD|GTQ|€)?\s*([\d.,]*\d)",
    re.I,
)
_ANY_AMOUNT = re.compile(r"(?:Q|\$|USD|GTQ|€)?\s?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2}|\d+[.,]\d{2})")
_VENCE = re.compile(
    r"(?:vigencia|vence|hasta el|finaliza)[^\d]{0,40}(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2})", re.I
)
_SALDO_ANTERIOR = re.compile(r"saldo\s+anterior\s*:?\s*(?:Q|\$|USD|GTQ|€)?\s*([\d.,]*\d)", re.I)
_PERIODO = re.compile(r"per[ií]odo\s*:?\s*(.+)", re.I)
_CUENTA = re.compile(r"cuenta\s+[A-Za-zÁÉÍÓÚáéíóúñ]+\s+([\d\-]{5,})", re.I)
_BANCO = re.compile(r"(banco\s+[A-Za-zÁÉÍÓÚáéíóúñ]+(?:\s+[A-Za-zÁÉÍÓÚáéíóúñ]+)?)", re.I)
_BENEFICIARIO = re.compile(r"beneficiario\s*:", re.I)
_OBJETO = re.compile(r"objeto\s*:", re.I)
_SALARIO = re.compile(r"salario[^\d\n]{0,20}([\d.,]*\d)", re.I)
_CUOTA_LAB = re.compile(r"cuota\s+laboral[^\d\n]{0,20}([\d.,]*\d)", re.I)
_CUOTA_PAT = re.compile(r"cuota\s+patronal[^\d\n]{0,20}([\d.,]*\d)", re.I)
_GARANTIA = re.compile(r"garant[ií]a[^\n]{0,100}", re.I)

CLAUSULAS_RIESGO = re.compile(
    r"penalizaci[oó]n|multa|rescisi[oó]n|garant[ií]a|renovaci[oó]n autom[aá]tica|"
    r"exclusividad|confidencialidad|inter[eé]s moratorio",
    re.I,
)


@dataclass
class Field:
    """Un dato extraído, con el texto exacto de donde salió (para el visor de origen)."""

    name: str
    value: object
    raw: str = ""
    method: str = "regla"  # regla | IA


@dataclass
class Extraction:
    tipo: str
    fields: dict[str, Field] = field(default_factory=dict)

    def get(self, name: str):
        f = self.fields.get(name)
        return f.value if f else None

    def put(self, name: str, value, raw: str = "", method: str = "regla") -> None:
        if value not in (None, ""):
            self.fields[name] = Field(name, value, raw or str(value), method)


def _line_value(text: str, pattern: re.Pattern) -> str:
    """Texto que sigue a la etiqueta (el patrón debe terminar justo después de los dos puntos)."""
    for line in text.splitlines():
        m = pattern.search(line)
        if m:
            return line[m.end():].strip()
    return ""


def extract_fields(text: str, tipo: str) -> Extraction:
    ex = Extraction(tipo=tipo)

    if m := _NUMERO.search(text):
        ex.put("Número", m.group(1), m.group(1))
    if m := _FECHA.search(text):
        ex.put("Fecha", parse_date(m.group(1)), m.group(1))
    if m := _NIT.search(text):
        nit = m.group(1)
        ex.put("NIT", nit, nit)
        valido = nit_valido(nit)
        if valido is not None:
            ex.put("NIT válido", "Sí" if valido else "No (dígito verificador)", nit)
    proveedor = _line_value(text, _PROVEEDOR)
    if proveedor:
        ex.put("Proveedor", proveedor, proveedor)

    total_label = {
        TIPO_ESTADO: "Saldo final",
        TIPO_CONTRATO: "Monto del contrato",
    }.get(tipo, "Total")
    totals = list(_TOTAL.finditer(text))
    if totals:
        raw = totals[-1].group(2)
        ex.put(total_label, parse_amount(raw), raw)
    else:
        amounts = [(parse_amount(m.group(1)), m.group(1)) for m in _ANY_AMOUNT.finditer(text)]
        amounts = [(a, r) for a, r in amounts if a is not None]
        if amounts:
            best = max(amounts, key=lambda ar: ar[0])
            ex.put(total_label, best[0], best[1])

    if tipo == TIPO_ESTADO:
        if m := _SALDO_ANTERIOR.search(text):
            ex.put("Saldo anterior", parse_amount(m.group(1)), m.group(1))
        if m := _PERIODO.search(text):
            ex.put("Período", m.group(1).strip(), m.group(1).strip())
        if m := _CUENTA.search(text):
            ex.put("Cuenta", m.group(1), m.group(1))
        if m := _BANCO.search(text):
            ex.put("Banco", m.group(1).title(), m.group(1))
    elif tipo == TIPO_CONTRATO:
        if m := _VENCE.search(text):
            ex.put("Vence", parse_date(m.group(1)), m.group(1))
        objeto = _line_value(text, _OBJETO)
        if objeto:
            ex.put("Objeto", objeto, objeto)
        partes = next((ln.strip() for ln in text.splitlines() if re.search(r"\bentre\b.+\by\b", ln, re.I)), "")
        if partes:
            ex.put("Partes", partes, partes)
        if m := _GARANTIA.search(text):
            ex.put("Garantías", m.group(0).strip(), m.group(0).strip())
    elif tipo == TIPO_PLANILLA:
        for label, rx in (("Salario", _SALARIO), ("Cuota laboral", _CUOTA_LAB), ("Cuota patronal", _CUOTA_PAT)):
            if m := rx.search(text):
                ex.put(label, parse_amount(m.group(1)), m.group(1))
    elif tipo == TIPO_COMPROBANTE:
        beneficiario = _line_value(text, _BENEFICIARIO)
        if beneficiario:
            ex.put("Beneficiario", beneficiario, beneficiario)
    return ex


def clause_lines(text: str) -> list[tuple[str, str]]:
    """Cláusulas de riesgo del texto: (nombre de la cláusula, línea completa recortada)."""
    found = []
    for line in text.splitlines():
        m = CLAUSULAS_RIESGO.search(line)
        if m:
            found.append((m.group(0).capitalize(), line.strip()[:110]))
    return found


def amount_of(ex: Extraction) -> Decimal | None:
    for name in ("Total", "Saldo final", "Monto del contrato"):
        value = ex.get(name)
        if isinstance(value, Decimal):
            return value
    return None


def date_of(ex: Extraction) -> date | None:
    value = ex.get("Fecha")
    return value if isinstance(value, date) else None
