# Paquete de procesador SUMARIA
"""Funciones para procesar cédulas Sumarias.

• fechas.py          → utilidades de fechas.
• deteccion.py       → detección de la cuenta asociada y validaciones.
• layout.py          → localiza la cuadrícula real de la plantilla.
• escritura.py       → escribe cuentas y saldos según ese layout.
• data_extraction.py → extracción y obtención de datos.
• insercion.py       → escritura en celdas fijas (plantillas anteriores).
• formulas.py        → helpers para manipular fórmulas.

`process_sumaria_file` es la API externa que agrupa todo.
"""

from __future__ import annotations

import logging

from openpyxl.workbook import Workbook

from .fechas import obtener_fechas_semestrales
from .deteccion import (
    determinar_cuenta_por_nombre_archivo,
    verificar_cuenta_en_balances,
    buscar_tabla_sumaria,
)
from .data_extraction import obtener_todas_cuentas_seccion
from .insercion import (
    insertar_datos_cuenta,
    insertar_multiples_cuentas,
    actualizar_fechas_encabezados,
)
from .layout import detectar_layout
from .escritura import escribir_sumaria

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Selección de las cuentas que corresponden a la cédula
# ---------------------------------------------------------------------

def _seccion_de_archivo(file_name):
    """Sección completa que toca volcar cuando la cédula es de un bloque entero."""
    nombre = file_name.upper()
    if 'PATRIMONIO' in nombre:
        return 'Patrimonio'
    if 'ESTADO RESULTADOS' in nombre or 'ESTADO_DE_RESULTADOS' in nombre:
        return 'ESTADO DE RESULTADOS'
    return None


def _cuentas_a_escribir(balances, fechas, file_name):
    """
    Devuelve {cuenta: {fecha: importe}} con lo que corresponde a esta cédula.

    · Cédulas de bloque (Patrimonio / Estado de Resultados): todas las cuentas
      de la sección.
    · Cédulas de un área concreta: la cuenta que nombra el archivo.
    · Cédulas genéricas ('N CEDULA_SUMARIA.xlsx'): ninguna — quedan en blanco
      para que el auditor las use con el área que necesite.
    """
    seccion = _seccion_de_archivo(file_name)
    if seccion:
        return obtener_todas_cuentas_seccion(balances, fechas, seccion) or {}

    cuenta = determinar_cuenta_por_nombre_archivo(file_name)
    if not cuenta:
        return {}

    existe, datos = verificar_cuenta_en_balances(balances, cuenta, fechas)
    return {cuenta: datos} if existe else {}


def _referencias_de(cuentas):
    """Referencia de sumaria (A-1, H-1, J-1…) para la columna Ref P/T."""
    try:
        from auditoria.services.referencias import ref_para_cuenta
    except Exception:
        return {}
    return {nombre: ref_para_cuenta(nombre) for nombre in cuentas}


# ---------------------------------------------------------------------
# API Principal del procesador SUMARIA
# ---------------------------------------------------------------------

def process_sumaria_file(
    workbook: Workbook,
    balances: dict[str, float],
    ajustes_reclasificaciones: dict[str, float],
    file_name: str,
):
    """
    Procesa archivos SUMARIA insertando los saldos del Excel Financiero.

    Recorre las hojas buscando una cuadrícula de cédula sumaria clásica
    (cuenta + cortes con fecha + ajustes Debe/Haber). Las sumarias
    especializadas de cada área —Activos Fijos, Inversiones, Inventarios,
    Construcciones, Intangible, Cuentas por Pagar, Préstamos, Patrimonio y
    Estado de Resultados— tienen columnas propias que no corresponden a los
    cortes del balance, así que se dejan intactas: reciben igualmente el
    encabezado, los datos del auditor y su referencia.
    """
    fechas_semestrales = obtener_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook

    fechas_ordenadas = sorted(fechas_semestrales)
    cuentas = _cuentas_a_escribir(balances, fechas_semestrales, file_name)
    if not cuentas:
        return workbook

    referencias = _referencias_de(cuentas)

    for hoja in workbook.worksheets:
        layout = detectar_layout(hoja)
        if not layout:
            continue

        escritas = escribir_sumaria(
            layout, cuentas, fechas_ordenadas, ajustes_reclasificaciones, referencias
        )
        if escritas:
            logger.info(
                'SUMARIA %s: %s cuenta(s) escritas en la hoja %r',
                file_name, escritas, hoja.title,
            )
        return workbook

    logger.info(
        'SUMARIA %s: la plantilla no es una cédula de saldos; se deja intacta.',
        file_name,
    )
    return workbook
