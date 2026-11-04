"""Normalización de importes, fechas, números de documento y NIT.

Convenciones de Guatemala: importes ``1,234.56``, fechas ``dd/mm/aaaa``. También se
aceptan ``1.234,56`` y ``aaaa-mm-dd``. Los importes se manejan como ``Decimal``.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

CENT = Decimal("0.01")
_THOUSANDS_COMMA = re.compile(r"^\d{1,3}(,\d{3})+$")
_THOUSANDS_DOT = re.compile(r"^\d{1,3}(\.\d{3}){2,}$")


def q2(value) -> Decimal:
    """Redondea a centavos (mitad hacia arriba)."""
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def parse_amount(value) -> Decimal | None:
    """Convierte un valor de celda o texto a ``Decimal`` con 2 decimales.

    Devuelve ``None`` si no hay un número reconocible. Nunca lanza excepción.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        return q2(value) if value.is_finite() else None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return q2(Decimal(repr(value)))
    if isinstance(value, (date, datetime)):
        return None

    text = str(value).strip()
    if not text:
        return None
    negative = (
        (text.startswith("(") and text.endswith(")"))
        or text.startswith("-")
        or text.endswith("-")
    )
    cleaned = re.sub(r"[^0-9.,]", "", text)
    if not re.search(r"\d", cleaned):
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if _THOUSANDS_COMMA.match(cleaned):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".", 1).replace(",", "")
    elif _THOUSANDS_DOT.match(cleaned):
        cleaned = cleaned.replace(".", "")
    elif cleaned.count(".") > 1:
        head, _, tail = cleaned.rpartition(".")
        cleaned = head.replace(".", "") + "." + tail

    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    amount = q2(amount)
    return -amount if negative else amount


_ISO_DATE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
_DMY_DATE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")
_EXCEL_EPOCH = date(1899, 12, 30)


def parse_date(value) -> date | None:
    """Convierte fechas de Excel, ``datetime`` o texto a ``date``."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if 20000 < value < 80000:
            return _EXCEL_EPOCH + timedelta(days=int(value))
        return None
    text = str(value).strip()
    match = _ISO_DATE.match(text)
    try:
        if match:
            return date(int(match[1]), int(match[2]), int(match[3]))
        match = _DMY_DATE.match(text)
        if match:
            year = int(match[3])
            if year < 100:
                year += 2000
            return date(year, int(match[2]), int(match[1]))
    except ValueError:
        return None
    return None


def norm_doc(value) -> str:
    """Número de documento sin ceros a la izquierda, guiones ni espacios."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"[^0-9a-z]", "", str(value).lower()).lstrip("0")


def norm_nit(value) -> str:
    return re.sub(r"[\s\-]", "", str(value or "")).upper()


def nit_valido(value) -> bool | None:
    """Valida el dígito verificador de un NIT guatemalteco.

    ``None`` si el texto no tiene forma de NIT. El algoritmo pondera los dígitos del
    cuerpo de ``n+1`` a ``2``, suma y obtiene ``(11 - suma mod 11) mod 11`` (10 = K).
    """
    nit = norm_nit(value)
    if not re.fullmatch(r"\d{2,}[0-9K]", nit):
        return None
    body, check = nit[:-1], nit[-1]
    weight = len(body) + 1
    total = 0
    for digit in body:
        total += int(digit) * weight
        weight -= 1
    expected = (11 - total % 11) % 11
    return check == ("K" if expected == 10 else str(expected))


def fmt_money(value, symbol: str = "Q ") -> str:
    if value is None:
        return ""
    return f"{symbol}{Decimal(value):,.2f}"


def fmt_num(value) -> str:
    return f"{Decimal(value):,.2f}"


def fmt_pct(ratio: Decimal | float, digits: int = 1) -> str:
    """Formatea una proporción (0.256) como porcentaje con coma de miles estándar."""
    pct = Decimal(str(ratio)) * 100
    return f"{pct.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP)} %"


def fmt_date(value: date | None) -> str:
    return value.strftime("%d/%m/%Y") if value else ""
