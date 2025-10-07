# Paquete de procesador SUMARIA
"""Funciones para procesar cédulas Sumarias.

• fechas.py         → utilidades de fechas.
• deteccion.py      → detección de cuentas, validaciones y búsqueda de tabla.
• data_extraction.py → extracción y obtención de datos.
• insercion.py      → escritura de datos, manejo de filas/estilos y encabezados.
• formulas.py       → helpers para manipular fórmulas.

`process_sumaria_file` es la API externa que agrupa todo.
"""

from __future__ import annotations

from openpyxl.workbook import Workbook

from .fechas import obtener_fechas_semestrales
from .deteccion import determinar_cuenta_por_nombre_archivo, verificar_cuenta_en_balances, buscar_tabla_sumaria
from .data_extraction import obtener_todas_cuentas_seccion
from .insercion import insertar_datos_cuenta, insertar_multiples_cuentas, actualizar_fechas_encabezados


# ---------------------------------------------------------------------
# API Principal del procesador SUMARIA
# ---------------------------------------------------------------------

def process_sumaria_file(
    workbook: Workbook,
    balances: dict[str, float],
    ajustes_reclasificaciones: dict[str, float],
    file_name: str,
):
    """Procesa archivos SUMARIA insertando datos de balances financieros."""

    sheet = workbook.active
    # 1. fechas disponibles
    fechas_semestrales = obtener_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook

    # 2. cuenta asociada según nombre de archivo
    cuenta_asociada = determinar_cuenta_por_nombre_archivo(file_name)
    if not cuenta_asociada:
        return workbook

    # 3. archivos especiales (patrimonio / estado resultados)
    es_archivo_especial = (
        "PATRIMONIO" in file_name.upper() or "ESTADO RESULTADOS" in file_name.upper()
    )

    if es_archivo_especial:
        seccion = (
            "Patrimonio" if "PATRIMONIO" in file_name.upper() else "ESTADO DE RESULTADOS"
        )

        todas_cuentas = obtener_todas_cuentas_seccion(balances, fechas_semestrales, seccion)
        if not todas_cuentas:
            return workbook

        tabla_info = buscar_tabla_sumaria(sheet)
        if not tabla_info:
            return workbook

        actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
        insertar_multiples_cuentas(sheet, todas_cuentas, fechas_semestrales, tabla_info, ajustes_reclasificaciones)
        
        return workbook

    # 4. camino normal (una cuenta)
    cuenta_existe, datos_cuenta = verificar_cuenta_en_balances(
        balances, cuenta_asociada, fechas_semestrales
    )
    if not cuenta_existe:
        return workbook

    tabla_info = buscar_tabla_sumaria(sheet)
    if not tabla_info:
        return workbook

    actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
    insertar_datos_cuenta(sheet, datos_cuenta, tabla_info, cuenta_asociada, ajustes_reclasificaciones)

    return workbook
