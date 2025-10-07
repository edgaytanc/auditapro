"""Extracción y obtención de datos para procesadores SUMARIA."""

from __future__ import annotations

from typing import Dict, List
import re

__all__ = [
    "encontrar_ajuste_para_cuenta",
    "obtener_todas_cuentas_seccion",
]


# ---------------------------------------------------------------------
# Búsqueda de ajustes/reclasificaciones para cuentas
# ---------------------------------------------------------------------

def encontrar_ajuste_para_cuenta(
    ajustes_reclasificaciones: Dict[str, Dict[str, float]],
    nombre_cuenta: str
) -> Dict[str, float] | None:
    """Busca coincidencias exactas o parciales en ajustes_reclasificaciones.

    Args:
        ajustes_reclasificaciones: Diccionario de ajustes/reclasificaciones
        nombre_cuenta: Nombre de la cuenta a buscar

    Returns:
        Diccionario con valores de debe/haber o None si no se encuentra
    """
    if not ajustes_reclasificaciones:
        return None

    # Coincidencia exacta
    if nombre_cuenta in ajustes_reclasificaciones:
        return ajustes_reclasificaciones[nombre_cuenta]

    # Coincidencia parcial
    nombre_normalizado = nombre_cuenta.lower().strip()
    for cuenta, valores in ajustes_reclasificaciones.items():
        cuenta_normalizada = cuenta.lower().strip()
        if nombre_normalizado in cuenta_normalizada or cuenta_normalizada in nombre_normalizado:
            return valores

    return None


# ---------------------------------------------------------------------
# Extracción de cuentas por sección desde balances
# ---------------------------------------------------------------------

def obtener_todas_cuentas_seccion(
    balances: Dict[str, float],
    fechas_semestrales: List[str],
    seccion: str,
) -> Dict[str, Dict[str, float]]:
    """Construye un dict {nombre_cuenta: {fecha: valor, ...}} para *seccion*."""

    todas_cuentas: Dict[str, Dict[str, float]] = {}
    patron = re.compile(fr"SEMESTRAL-(.*?)-{seccion}-(.*)")

    for clave, valor in balances.items():
        m = patron.match(clave)
        if not m:
            continue
        fecha, nombre_cuenta = m.groups()
        if fecha not in fechas_semestrales:
            continue
        todas_cuentas.setdefault(nombre_cuenta, {})[fecha] = valor

    return todas_cuentas