"""Detección de cuenta asociada y verificación en balances para procesadores SUMARIA."""

from __future__ import annotations

import re
import logging
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)

__all__ = [
    "determinar_cuenta_por_nombre_archivo",
    "verificar_cuenta_en_balances",
]


_MAPEO_CUENTAS: dict[str, str] = {
    "CAJA": "Caja y Bancos",
    "BANCO": "Caja y Bancos",
    "COBRAR": "Cuentas por Cobrar",
    "CLIENTE": "Cuentas por Cobrar",
    "INVENTARIO": "Inventarios",
    "INVERSION": "Inversiones",
    "CONSTRUCCION": "Construcciones en Proceso",
    "PROCESO": "Construcciones en Proceso",
    "ACTIVO FIJO": "Propiedad, Planta y Equipo",
    "PROPIEDAD": "Propiedad, Planta y Equipo",
    "PLANTA": "Propiedad, Planta y Equipo",
    "EQUIPO": "Propiedad, Planta y Equipo",
    "INTANGIBLE": "Activo Intangible",
    "PAGAR": "Cuentas por Pagar",
    "PROVEEDOR": "Cuentas por Pagar",
    "PASIVO LARGO PLAZO": "Pasivo Largo Plazo",
    "PASIVO": "Pasivo",
    "PRESTAMO": "Préstamos por Pagar",
    "FINANCIAMIENTO": "Préstamos por Pagar",
    "PATRIMONIO": "Patrimonio",
    "CAPITAL": "Capital",
    "RESULTADO": "Estado de Resultados",
    "INGRESO": "Ingresos",
    "EGRESO": "Egresos",
    "GASTO": "Gastos",
    "COSTO": "Costos",
}


def determinar_cuenta_por_nombre_archivo(file_name: str) -> str | None:
    """Intenta inferir la cuenta contable a partir del nombre del archivo.

    Devuelve el nombre normalizado de la cuenta o None si no puede determinarse.
    """

    logger.debug(f"Iniciando detección de cuenta para archivo {file_name}")

    # Quitar extensión y números iniciales
    nombre_limpio = re.sub(r"^\d+\s*", "", file_name.replace(".xlsx", ""))

    logger.debug(f"Nombre limpio del archivo: {nombre_limpio}")

    # Buscar por palabras clave, de más largas a más cortas
    for palabra_clave in sorted(_MAPEO_CUENTAS, key=len, reverse=True):
        if palabra_clave in nombre_limpio.upper():
            logger.debug(f"Encontrada coincidencia con palabra clave {palabra_clave}")
            return _MAPEO_CUENTAS[palabra_clave]

    # Fallback: extraer texto posterior a "SUMARIA "
    if m := re.search(r"SUMARIA\s+(.*?)(?:\s+|$)", nombre_limpio.upper()):
        logger.debug(f"Encontrada coincidencia con fallback SUMARIA {m.group(1)}")
        return m.group(1).title()

    logger.warning(f"No se pudo determinar la cuenta para archivo {file_name}")
    return None


def verificar_cuenta_en_balances(
    balances: Dict[str, float],
    cuenta_asociada: str,
    fechas_semestrales: List[str],
) -> Tuple[bool, Dict[str, float]]:
    """Comprueba la existencia de *cuenta_asociada* en *balances* y
    devuelve los valores por fecha.

    Retorna `(existe, datos_por_fecha)`.
    """

    logger.debug(f"Iniciando verificación de cuenta {cuenta_asociada} en balances")

    datos_cuenta: dict[str, float] = {}
    cuenta_existe = False
    cuenta_normalizada = cuenta_asociada.lower().strip()

    for seccion in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]:
        for fecha in fechas_semestrales:
            clave_exacta = f"SEMESTRAL-{fecha}-{seccion}-{cuenta_asociada}"
            if clave_exacta in balances:
                logger.debug(f"Encontrada coincidencia exacta con clave {clave_exacta}")
                datos_cuenta[fecha] = balances[clave_exacta]
                cuenta_existe = True
                continue

            # Buscar coincidencias parciales si no hay exactas
            if fecha not in datos_cuenta:
                prefijo = f"SEMESTRAL-{fecha}-{seccion}-"
                for clave, valor in balances.items():
                    if clave.startswith(prefijo):
                        nombre_cuenta = "-".join(clave.split("-")[3:]).lower().strip()
                        if cuenta_normalizada in nombre_cuenta or nombre_cuenta in cuenta_normalizada:
                            logger.debug(f"Encontrada coincidencia parcial con clave {clave}")
                            datos_cuenta[fecha] = valor
                            cuenta_existe = True
                            break

    if cuenta_existe:
        logger.info(f"Cuenta {cuenta_asociada} encontrada en balances")
    else:
        logger.warning(f"Cuenta {cuenta_asociada} no encontrada en balances")

    return cuenta_existe, datos_cuenta
