# Paquete de procesador SUMARIA
"""Funciones para procesar cédulas Sumarias.

• fechas.py      → utilidades de fechas.
• deteccion.py   → detección de cuentas y validaciones en balances.
• tabla.py       → búsqueda y actualización de la tabla en la hoja.
• insercion.py   → escritura de datos y manejo de filas/estilos.
• formulas.py    → helpers para manipular fórmulas.

`process_sumaria_file` es la API externa que agrupa todo.
"""

from __future__ import annotations

import logging
from openpyxl.workbook import Workbook

from .fechas import obtener_fechas_semestrales
from .deteccion import determinar_cuenta_por_nombre_archivo, verificar_cuenta_en_balances
from .tabla import buscar_tabla_sumaria, actualizar_fechas_encabezados
from .insercion import insertar_datos_cuenta, insertar_multiples_cuentas, obtener_todas_cuentas_seccion

logger = logging.getLogger(__name__)


def process_sumaria_file(
    workbook: Workbook,
    balances: dict[str, float],
    ajustes_reclasificaciones: dict[str, float],
    file_name: str,
):
    """Procesa archivos SUMARIA insertando datos de balances financieros."""

    logger.info(f"=== PROCESANDO ARCHIVO SUMARIA: {file_name} ===")
    
    # DEBUG: Registrar nombres de cuentas en ajustes_reclasificaciones
    if ajustes_reclasificaciones:
        logger.info(f"CUENTAS EN AJUSTES_RECLASIFICACIONES ({len(ajustes_reclasificaciones)}):")
        for cuenta, valores in ajustes_reclasificaciones.items():
            logger.info(f"  - '{cuenta}': {valores}")
    else:
        logger.info("AJUSTES_RECLASIFICACIONES está vacío o es None")

    sheet = workbook.active
    # 1. fechas disponibles
    fechas_semestrales = obtener_fechas_semestrales(balances)
    if not fechas_semestrales:
        logger.warning("No se encontraron fechas semestrales en balances")
        return workbook

    logger.info(f"FECHAS SEMESTRALES ENCONTRADAS: {fechas_semestrales}")

    # 2. cuenta asociada según nombre de archivo
    cuenta_asociada = determinar_cuenta_por_nombre_archivo(file_name)
    if not cuenta_asociada:
        logger.warning(f"No se pudo determinar cuenta asociada para archivo: {file_name}")
        return workbook

    logger.info(f"CUENTA ASOCIADA DETERMINADA: '{cuenta_asociada}'")

    # 3. archivos especiales (patrimonio / estado resultados)
    es_archivo_especial = (
        "PATRIMONIO" in file_name.upper() or "ESTADO RESULTADOS" in file_name.upper()
    )

    if es_archivo_especial:
        seccion = (
            "Patrimonio" if "PATRIMONIO" in file_name.upper() else "ESTADO DE RESULTADOS"
        )
        logger.info(f"ARCHIVO ESPECIAL DETECTADO - SECCIÓN: {seccion}")
        
        todas_cuentas = obtener_todas_cuentas_seccion(balances, fechas_semestrales, seccion)
        if not todas_cuentas:
            logger.warning(f"No se encontraron cuentas para la sección: {seccion}")
            return workbook

        # DEBUG: Registrar todas las cuentas encontradas en balances para esta sección
        logger.info(f"CUENTAS ENCONTRADAS EN BALANCES PARA SECCIÓN '{seccion}' ({len(todas_cuentas)}):")
        for cuenta, datos in todas_cuentas.items():
            logger.info(f"  - '{cuenta}': {datos}")

        tabla_info = buscar_tabla_sumaria(sheet)
        if not tabla_info:
            logger.warning("No se encontró información de la tabla SUMARIA")
            return workbook

        actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
        insertar_multiples_cuentas(sheet, todas_cuentas, fechas_semestrales, tabla_info, ajustes_reclasificaciones)
        
        logger.info(f"PROCESAMIENTO COMPLETADO PARA ARCHIVO ESPECIAL: {file_name}")
        return workbook

    # 4. camino normal (una cuenta)
    cuenta_existe, datos_cuenta = verificar_cuenta_en_balances(
        balances, cuenta_asociada, fechas_semestrales
    )
    if not cuenta_existe:
        logger.warning(f"No se encontró cuenta '{cuenta_asociada}' en balances")
        return workbook

    logger.info(f"CUENTA '{cuenta_asociada}' ENCONTRADA EN BALANCES")

    tabla_info = buscar_tabla_sumaria(sheet)
    if not tabla_info:
        logger.warning("No se encontró información de la tabla SUMARIA")
        return workbook

    actualizar_fechas_encabezados(sheet, fechas_semestrales, tabla_info)
    insertar_datos_cuenta(sheet, datos_cuenta, tabla_info, cuenta_asociada, ajustes_reclasificaciones)

    logger.info(f"PROCESAMIENTO COMPLETADO PARA ARCHIVO: {file_name}")
    return workbook
