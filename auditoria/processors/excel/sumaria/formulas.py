"""Helpers para manipular fórmulas de openpyxl en procesadores SUMARIA."""

from __future__ import annotations

import re

__all__ = ["ajustar_formula_para_nueva_fila", "desplazar_referencias_de_fila"]


# Referencia de celda dentro de una fórmula: columna (con o sin $) + fila.
# El lookbehind evita partir palabras ('LOG10' no es una referencia) y el
# lookahead descarta llamadas a función.
_PATRON_REFERENCIA = re.compile(
    r"(?<![A-Za-z0-9_$])(\$?[A-Za-z]{1,3}\$?)(\d+)(?![\d(])"
)


# ---------------------------------------------------------------------
# Ajuste de referencias de fila en fórmulas Excel
# ---------------------------------------------------------------------

def ajustar_formula_para_nueva_fila(formula: str, fila_origen: int, fila_destino: int) -> str:
    """
    Reescribe las referencias de `fila_origen` a `fila_destino` en la fórmula,
    tanto absolutas ('$10') como relativas ('G10'), igual que hace Excel al
    rellenar hacia abajo. Las referencias a OTRAS filas (encabezados, totales)
    se conservan.
    """

    def _reemplazo(match):
        columna, fila = match.group(1), int(match.group(2))
        if fila == fila_origen:
            return f"{columna}{fila_destino}"
        return match.group(0)

    return _PATRON_REFERENCIA.sub(_reemplazo, formula)


def desplazar_referencias_de_fila(formula: str, desde_fila: int, delta: int) -> str:
    """
    Desplaza en `delta` las referencias cuya fila sea >= `desde_fila`.

    openpyxl `insert_rows` mueve las celdas pero NO traduce las fórmulas que
    quedaron debajo de la inserción (p. ej. el bloque 'VERIFICACIÓN DE
    DIFERENCIAS' que apunta a la fila de totales); este helper las corrige.
    """

    def _reemplazo(match):
        columna, fila = match.group(1), int(match.group(2))
        if fila >= desde_fila:
            return f"{columna}{fila + delta}"
        return match.group(0)

    return _PATRON_REFERENCIA.sub(_reemplazo, formula)
