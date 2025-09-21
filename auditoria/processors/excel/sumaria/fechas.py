"""Módulo de utilidades de fechas para procesadores SUMARIA."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List


# ---------------------------------------------------------------------
# Extracción de fechas semestrales desde balances
# ---------------------------------------------------------------------

def obtener_fechas_semestrales(balances: dict[str, float]) -> List[str]:
    """Extrae todas las fechas semestrales (YYYY-MM-DD) presentes en las claves
    del diccionario de *balances*.

    Las claves relevantes tienen formato ``SEMESTRAL-<fecha>-Seccion-...``.
    Devuelve una lista ordenada ascendentemente.
    """

    patron_fecha = re.compile(r"SEMESTRAL-(\d{4}-\d{2}-\d{2})")
    fechas: set[str] = set()

    for clave in balances:
        if m := patron_fecha.search(clave):
            fechas.add(m.group(1))

    return sorted(fechas)


# ---------------------------------------------------------------------
# Formateo de fechas para encabezados
# ---------------------------------------------------------------------

def _formatear_fecha_ddmmaa(fecha_iso: str) -> str:
    """Convierte 'YYYY-MM-DD' → 'DD/MM/YYYY'."""

    yyyy, mm, dd = fecha_iso.split("-")
    return f"{dd}/{mm}/{yyyy}"
