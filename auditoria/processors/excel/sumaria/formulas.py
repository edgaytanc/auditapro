"""Helpers para manipular fórmulas de openpyxl en procesadores SUMARIA."""

from __future__ import annotations

__all__ = ["ajustar_formula_para_nueva_fila"]


# ---------------------------------------------------------------------
# Ajuste de referencias de fila en fórmulas Excel
# ---------------------------------------------------------------------

def ajustar_formula_para_nueva_fila(formula: str, fila_origen: int, fila_destino: int) -> str:
    """Reemplaza las referencias de `fila_origen` por `fila_destino` en la fórmula.

    Nota: Asume referencias absolutas tipo ``$13``. Para casos más complejos se
    requerirá un parser más robusto.
    """

    return formula.replace(f"${fila_origen}", f"${fila_destino}")
