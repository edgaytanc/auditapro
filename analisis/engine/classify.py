"""Etapa 01 · Clasificación por página (reglas; la IA opcional solo resuelve dudas)."""
from __future__ import annotations

import re
from dataclasses import dataclass

TIPO_FACTURA = "Factura"
TIPO_ESTADO = "Estado de cuenta"
TIPO_CONTRATO = "Contrato"
TIPO_PLANILLA = "Planilla / nómina"
TIPO_COMPROBANTE = "Comprobante de pago"
TIPO_AUXILIAR = "Auxiliar / reporte"
TIPO_OTRO = "Otro"
TIPO_SIN_TEXTO = "Evidencia sin texto"

_RULES: list[tuple[str, list[re.Pattern]]] = [
    (TIPO_FACTURA, [re.compile(p, re.I) for p in (r"factura", r"invoice", r"\bdte\b", r"\bfel\b", r"serie\s*[:#]")]),
    (TIPO_ESTADO, [re.compile(p, re.I) for p in (r"estado de cuenta", r"saldo anterior", r"saldo final", r"movimientos del per")]),
    (TIPO_CONTRATO, [re.compile(p, re.I) for p in (r"contrato", r"cl[aá]usula", r"las partes", r"el contratante")]),
    (TIPO_PLANILLA, [re.compile(p, re.I) for p in (r"planilla", r"n[oó]mina", r"\bigss\b", r"salario", r"seguridad social")]),
    (TIPO_COMPROBANTE, [re.compile(p, re.I) for p in (r"recibo", r"transferencia", r"comprobante", r"cheque n")]),
]


@dataclass
class Classification:
    tipo: str
    confianza: float
    metodo: str  # regla | IA | ninguno


def classify_text(text: str) -> Classification:
    """Elige el tipo con más indicios distintos; en empate gana el orden de las reglas.

    Por ejemplo, un contrato que menciona una «factura» tiene más indicios de contrato
    (contrato, cláusula, las partes) que de factura, y se clasifica como contrato.
    """
    best_tipo, best_hits = TIPO_OTRO, 0
    for tipo, patterns in _RULES:
        hits = sum(1 for p in patterns if p.search(text))
        if hits > best_hits:
            best_tipo, best_hits = tipo, hits
    if best_hits == 0:
        return Classification(TIPO_OTRO, 0.0, "ninguno")
    return Classification(best_tipo, min(0.95, 0.55 + 0.15 * best_hits), "regla")


TIPOS_CRUZABLES = (TIPO_FACTURA, TIPO_COMPROBANTE)
