"""Inserción de datos y manipulación de filas/estilos para la tabla SUMARIA."""

from __future__ import annotations

import logging
from typing import Dict, List

from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment
from openpyxl.worksheet.worksheet import Worksheet

from .formulas import ajustar_formula_para_nueva_fila

logger = logging.getLogger(__name__)

__all__ = [
    "insertar_datos_cuenta",
    "obtener_todas_cuentas_seccion",
    "insertar_multiples_cuentas",
    "encontrar_ajuste_para_cuenta",
]


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
        logger.debug(f"Encontrada coincidencia exacta para ajustes: '{nombre_cuenta}'")
        return ajustes_reclasificaciones[nombre_cuenta]
    
    # Coincidencia parcial
    nombre_normalizado = nombre_cuenta.lower().strip()
    for cuenta, valores in ajustes_reclasificaciones.items():
        cuenta_normalizada = cuenta.lower().strip()
        if nombre_normalizado in cuenta_normalizada or cuenta_normalizada in nombre_normalizado:
            logger.debug(f"Encontrada coincidencia parcial para ajustes: '{nombre_cuenta}' con '{cuenta}'")
            return valores
    
    logger.debug(f"No se encontraron ajustes para cuenta: '{nombre_cuenta}'")
    return None


# ---------------------------------------------------------------------
# Inserción sencilla (una cuenta)
# ---------------------------------------------------------------------

def insertar_datos_cuenta(
    sheet: Worksheet,
    datos_cuenta: Dict[str, float],
    tabla_info: Dict[str, int | List[int]],
    nombre_cuenta: str = "TOTAL",
    ajustes_reclasificaciones: Dict[str, Dict[str, float]] = None,
) -> None:
    """Escribe *datos_cuenta* en la fila 13 de la plantilla."""

    logger.debug(f"Inserción de cuenta {nombre_cuenta} en la fila 13")
    fechas_ordenadas = sorted(datos_cuenta.keys())
    sheet["B13"].value = nombre_cuenta
    celdas_valores = ["E13", "F13", "G13", "J13"]
    for idx, celda in enumerate(celdas_valores):
        if idx < len(fechas_ordenadas):
            fecha = fechas_ordenadas[idx]
            if fecha in datos_cuenta:
                sheet[celda].value = datos_cuenta[fecha]
                sheet[celda].alignment = Alignment(horizontal="right")
                logger.debug(f"Inserción de valor {datos_cuenta[fecha]} en celda {celda}")
    
    # Insertar valores de ajustes/reclasificaciones usando la nueva función
    valores_ajuste = encontrar_ajuste_para_cuenta(ajustes_reclasificaciones, nombre_cuenta)
    if valores_ajuste:
        logger.debug(f"Ajustes/reclasificaciones encontrados para cuenta {nombre_cuenta}")
        if 'debe' in valores_ajuste:
            sheet["H13"].value = valores_ajuste['debe']
            sheet["H13"].alignment = Alignment(horizontal="right")
            logger.debug(f"Inserción de valor {valores_ajuste['debe']} en celda H13")
        if 'haber' in valores_ajuste:
            sheet["I13"].value = valores_ajuste['haber']
            sheet["I13"].alignment = Alignment(horizontal="right")
            logger.debug(f"Inserción de valor {valores_ajuste['haber']} en celda I13")


# ---------------------------------------------------------------------
# Helpers para obtener todas las cuentas de una sección
# ---------------------------------------------------------------------

def obtener_todas_cuentas_seccion(
    balances: Dict[str, float],
    fechas_semestrales: List[str],
    seccion: str,
) -> Dict[str, Dict[str, float]]:
    """Construye un dict {nombre_cuenta: {fecha: valor, ...}} para *seccion*."""

    import re

    logger.debug(f"Obteniendo cuentas de sección {seccion}")
    todas_cuentas: Dict[str, Dict[str, float]] = {}
    patron = re.compile(fr"SEMESTRAL-(.*?)-{seccion}-(.*)")

    for clave, valor in balances.items():
        m = patron.match(clave)
        if not m:
            continue
        fecha, nombre_cuenta = m.groups()
        if fecha not in fechas_semestrales:
            continue
        logger.debug(f"Cuenta {nombre_cuenta} encontrada en balances")
        todas_cuentas.setdefault(nombre_cuenta, {})[fecha] = valor

    return todas_cuentas


# ---------------------------------------------------------------------
# Inserción múltiple (varias cuentas y filas dinámicas)
# ---------------------------------------------------------------------

def insertar_multiples_cuentas(
    sheet: Worksheet,
    todas_cuentas: Dict[str, Dict[str, float]],
    fechas_semestrales: List[str],
    tabla_info: Dict[str, int | List[int]],
    ajustes_reclasificaciones: Dict[str, Dict[str, float]] = None,
) -> None:
    """Inserta varias cuentas, creando filas adicionales después de la 13 si es necesario."""

    logger.debug("Inserción múltiple de cuentas")
    fechas_ordenadas = sorted(fechas_semestrales)
    cuentas_ordenadas = sorted(todas_cuentas.keys())

    filas_necesarias = len(cuentas_ordenadas)
    filas_disponibles = 1  # la plantilla tiene 1 fila vacía (13)
    filas_a_insertar = max(0, filas_necesarias - filas_disponibles)

    # Guardar rangos combinados de la fila 13
    celdas_combinadas_originales = []
    for merged_range in sheet.merged_cells.ranges:
        if 13 in range(merged_range.min_row, merged_range.max_row + 1):
            celdas_combinadas_originales.append(
                {
                    "min_row": merged_range.min_row,
                    "max_row": merged_range.max_row,
                    "min_col": merged_range.min_col,
                    "max_col": merged_range.max_col,
                }
            )

    if filas_a_insertar:
        logger.debug(f"Inserción de {filas_a_insertar} filas adicionales")
        # Copiar estilos/fórmulas de la fila 13
        estilos_fila_13 = {}
        formulas_fila_13 = {}
        for col in range(1, sheet.max_column + 1):
            celda = sheet.cell(row=13, column=col)
            estilos_fila_13[col] = {
                "font": celda.font.copy() if celda.font else None,
                "border": celda.border.copy() if celda.border else None,
                "fill": celda.fill.copy() if celda.fill else None,
                "number_format": celda.number_format,
                "alignment": celda.alignment.copy() if celda.alignment else None,
                "protection": celda.protection.copy() if celda.protection else None,
            }
            if celda.data_type == "f":
                formulas_fila_13[col] = celda.value

        sheet.insert_rows(14, filas_a_insertar)

        for i in range(filas_a_insertar):
            fila_destino = 14 + i
            for col, estilos in estilos_fila_13.items():
                celda_dest = sheet.cell(row=fila_destino, column=col)
                if estilos["font"]:
                    celda_dest.font = estilos["font"]
                if estilos["border"]:
                    celda_dest.border = estilos["border"]
                if estilos["fill"]:
                    celda_dest.fill = estilos["fill"]
                celda_dest.number_format = estilos["number_format"]
                if estilos["alignment"]:
                    celda_dest.alignment = estilos["alignment"]
                if estilos["protection"]:
                    celda_dest.protection = estilos["protection"]

                # Ajustar fórmulas
                if col in formulas_fila_13:
                    formula_orig = formulas_fila_13[col]
                    if isinstance(formula_orig, str) and formula_orig.startswith("="):
                        celda_dest.value = ajustar_formula_para_nueva_fila(
                            formula_orig, 13, fila_destino
                        )

            # Restaurar combinaciones
            for rng in celdas_combinadas_originales:
                if rng["max_col"] > rng["min_col"]:
                    rango = f"{get_column_letter(rng['min_col'])}{fila_destino}:{get_column_letter(rng['max_col'])}{fila_destino}"
                    sheet.merge_cells(rango)

    # Escribir datos en filas
    for i, nombre_cuenta in enumerate(cuentas_ordenadas):
        fila = 13 + i
        sheet[f"B{fila}"].value = nombre_cuenta
        logger.debug(f"Inserción de cuenta {nombre_cuenta} en fila {fila}")
        celdas_valores_col = ["E", "F", "G", "J"]
        for j, col_letra in enumerate(celdas_valores_col):
            if j < len(fechas_ordenadas):
                fecha = fechas_ordenadas[j]
                if fecha in todas_cuentas[nombre_cuenta]:
                    sheet[f"{col_letra}{fila}"].value = todas_cuentas[nombre_cuenta][fecha]
                    sheet[f"{col_letra}{fila}"].alignment = Alignment(horizontal="right")
                    logger.debug(f"Inserción de valor {todas_cuentas[nombre_cuenta][fecha]} en celda {col_letra}{fila}")
        
        # Insertar valores de ajustes/reclasificaciones usando la nueva función
        valores_ajuste = encontrar_ajuste_para_cuenta(ajustes_reclasificaciones, nombre_cuenta)
        if valores_ajuste:
            logger.debug(f"Ajustes/reclasificaciones encontrados para cuenta {nombre_cuenta}")
            if 'debe' in valores_ajuste:
                sheet[f"H{fila}"].value = valores_ajuste['debe']
                sheet[f"H{fila}"].alignment = Alignment(horizontal="right")
                logger.debug(f"Inserción de valor {valores_ajuste['debe']} en celda H{fila}")
            if 'haber' in valores_ajuste:
                sheet[f"I{fila}"].value = valores_ajuste['haber']
                sheet[f"I{fila}"].alignment = Alignment(horizontal="right")
                logger.debug(f"Inserción de valor {valores_ajuste['haber']} en celda I{fila}")
