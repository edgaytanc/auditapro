"""Detección de cuenta asociada y verificación en balances para procesadores SUMARIA."""

from __future__ import annotations

import re
from typing import Tuple, Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

__all__ = [
    "determinar_cuenta_por_nombre_archivo",
    "verificar_cuenta_en_balances",
    "cuenta_importada_equivalente",
    "buscar_tabla_sumaria",
    "numero_de_cedula_generica",
    "cuentas_sin_cedula_propia",
]

# Secciones cuyas cuentas ya tienen cédula de bloque propia (Patrimonio y
# Estado de Resultados vuelcan la sección entera), así que sus cuentas no se
# reparten entre las cédulas genéricas.
_SECCIONES_CON_CEDULA_PROPIA = ("Patrimonio", "ESTADO DE RESULTADOS")

# Secciones cuyas cuentas sí pueden quedar sin cédula propia
_SECCIONES_REPARTIBLES = ("Activo", "Pasivo")


# ---------------------------------------------------------------------
# Mapeo de palabras clave a nombres de cuentas contables
# ---------------------------------------------------------------------

_MAPEO_CUENTAS: dict[str, str] = {
    "CAJA": "Caja y Bancos",
    "BANCO": "Caja y Bancos",
    # Los papeles de Revisoría nombran esta área por la cuenta del Excel
    "EFECTIVO": "Caja y Bancos",
    "EQUIVALENTE": "Caja y Bancos",
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


# ---------------------------------------------------------------------
# Detección de cuenta por nombre de archivo
# ---------------------------------------------------------------------

def determinar_cuenta_por_nombre_archivo(file_name: str) -> str | None:
    """Intenta inferir la cuenta contable a partir del nombre del archivo.

    Devuelve el nombre normalizado de la cuenta o None si no puede determinarse.
    """

    # Quitar extensión y números iniciales
    nombre_limpio = re.sub(r"^\d+\s*", "", file_name.replace(".xlsx", ""))

    # Buscar por palabras clave, de más largas a más cortas
    for palabra_clave in sorted(_MAPEO_CUENTAS, key=len, reverse=True):
        if palabra_clave in nombre_limpio.upper():
            return _MAPEO_CUENTAS[palabra_clave]

    # Fallback: extraer texto posterior a "SUMARIA "
    if m := re.search(r"SUMARIA\s+(.*?)(?:\s+|$)", nombre_limpio.upper()):
        return m.group(1).title()

    return None


# ---------------------------------------------------------------------
# Verificación de existencia de cuenta en balances
# ---------------------------------------------------------------------

# Nombres equivalentes usados por el NUEVO formato de importación
# ("Revisoría 2025 con subcuentas"). Solo se consultan como fallback,
# cuando la búsqueda normal no encuentra la cuenta.
_EQUIVALENCIAS_CUENTAS: dict[str, tuple[str, ...]] = {
    "Caja y Bancos": ("Efectivo y Equivalentes",),
}


def numero_de_cedula_generica(file_name: str) -> Optional[int]:
    """
    Número de una cédula genérica ('9 CEDULA_SUMARIA.xlsx' -> 9), o None.

    Son las plantillas en blanco de 'OTRAS CEDULAS SUMARIAS', que no nombran
    ninguna cuenta en particular.
    """
    encontrado = re.match(r"^\s*(\d+)\s*CEDULA[_ ]SUMARIA\s*\.xlsx$",
                          (file_name or "").strip(), re.IGNORECASE)
    return int(encontrado.group(1)) if encontrado else None


def cuentas_sin_cedula_propia(
    balances: Dict[str, float],
    fechas_semestrales: List[str],
) -> List[str]:
    """
    Cuentas importadas del Activo y del Pasivo que NO tienen cédula propia.

    Son las que el cliente agrega a su Excel Financiero (p. ej. 'Contratos'):
    como no las reclama ninguna cédula de área, se reparten en orden entre las
    cédulas de 'OTRAS CEDULAS SUMARIAS'. El orden es estable (sección y luego
    nombre) para que una cuenta no cambie de cédula entre descargas.
    """
    from .data_extraction import obtener_todas_cuentas_seccion

    pendientes: List[str] = []
    for seccion in _SECCIONES_REPARTIBLES:
        cuentas = obtener_todas_cuentas_seccion(balances, fechas_semestrales, seccion)
        for nombre in sorted(cuentas):
            limpio = _sin_sufijo_tipo(nombre)
            if not limpio or _tiene_cedula_propia(limpio):
                continue
            if limpio.lower().startswith(("total", "suma")):
                continue  # filas de totales, no son cuentas
            if limpio not in pendientes:
                pendientes.append(limpio)
    return pendientes


def _sin_sufijo_tipo(nombre_cuenta: str) -> str:
    """
    Quita el tipo de cuenta que la clave del balance lleva al final.

    Las claves se arman como '<balance>-<fecha>-<sección>-<cuenta>-<tipo>'
    (por ejemplo '...-Activo-Contratos-NT'), así que al leer el nombre viene
    pegado ese '-NT' que no debe salir impreso en la cédula.
    """
    limpio = (nombre_cuenta or "").strip()
    return re.sub(r"-[A-Z]{1,3}$", "", limpio).strip()


def _tiene_cedula_propia(nombre_cuenta: str) -> bool:
    """
    True si la cuenta ya la recoge una cédula de área.

    Se comprueba sobre el NOMBRE de la cuenta (no sobre los balances) con las
    mismas palabras clave que nombran los archivos de cédula, más los nombres
    equivalentes del formato nuevo ('Efectivo y Equivalentes' es la cédula de
    Caja y Bancos).
    """
    texto = (nombre_cuenta or "").upper()
    if not texto:
        return False

    if any(palabra in texto for palabra in _MAPEO_CUENTAS):
        return True

    for equivalentes in _EQUIVALENCIAS_CUENTAS.values():
        for equivalente in equivalentes:
            if equivalente.upper() in texto:
                return True
    return False


def verificar_cuenta_en_balances(
    balances: Dict[str, float],
    cuenta_asociada: str,
    fechas_semestrales: List[str],
) -> Tuple[bool, Dict[str, float]]:
    """Comprueba la existencia de *cuenta_asociada* en *balances* y
    devuelve los valores por fecha.

    Retorna `(existe, datos_por_fecha)`.
    """

    datos_cuenta: dict[str, float] = {}
    cuenta_existe = False
    cuenta_normalizada = cuenta_asociada.lower().strip()

    for seccion in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]:
        for fecha in fechas_semestrales:
            clave_exacta = f"SEMESTRAL-{fecha}-{seccion}-{cuenta_asociada}"
            if clave_exacta in balances:
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
                            datos_cuenta[fecha] = valor
                            cuenta_existe = True
                            break

    # 👇 Fallback: probar los nombres equivalentes del nuevo formato
    if not cuenta_existe:
        for nombre_equivalente in _EQUIVALENCIAS_CUENTAS.get(cuenta_asociada, ()):
            cuenta_existe, datos_cuenta = verificar_cuenta_en_balances(
                balances, nombre_equivalente, fechas_semestrales
            )
            if cuenta_existe:
                break

    return cuenta_existe, datos_cuenta


def cuenta_importada_equivalente(
    balances: Dict[str, float],
    cuenta_asociada: str,
    fechas_semestrales: List[str],
) -> Optional[str]:
    """
    Devuelve el nombre REAL con que la cuenta está en los balances importados
    ('Caja y Bancos' → 'Efectivo y Equivalentes' si así vino en el Excel),
    o None si no existe. Sirve para buscar las subcuentas de la cuenta.
    """
    candidatos = (cuenta_asociada,) + _EQUIVALENCIAS_CUENTAS.get(cuenta_asociada, ())

    for candidato in candidatos:
        normalizada = candidato.lower().strip()
        for seccion in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]:
            for fecha in fechas_semestrales:
                clave_exacta = f"SEMESTRAL-{fecha}-{seccion}-{candidato}"
                if clave_exacta in balances:
                    return candidato

                prefijo = f"SEMESTRAL-{fecha}-{seccion}-"
                for clave in balances:
                    if clave.startswith(prefijo):
                        nombre_cuenta = "-".join(clave.split("-")[3:]).strip()
                        nombre_norm = nombre_cuenta.lower()
                        if normalizada in nombre_norm or nombre_norm in normalizada:
                            return nombre_cuenta
    return None


# ---------------------------------------------------------------------
# Localización de tabla SUMARIA en hoja Excel
# ---------------------------------------------------------------------

def _es_encabezado_saldos(valor) -> bool:
    """
    Detecta la leyenda de saldos de la tabla SUMARIA.
    Acepta la leyenda clásica 'Saldos s/ Balance' y la de las plantillas
    nuevas 'SALDOS SEGÚN BALANCE GENERAL' (con o sin tilde).
    """
    if not isinstance(valor, str):
        return False
    texto = valor.upper()
    return (
        "SALDOS S/ BALANCE" in texto
        or "SALDOS SEGÚN BALANCE" in texto
        or "SALDOS SEGUN BALANCE" in texto
    )


def buscar_tabla_sumaria(sheet: Worksheet) -> Optional[Dict[str, int | List[int]]]:
    """Intenta ubicar la tabla SUMARIA en *sheet*.

    Devuelve un diccionario con:
    - fila_titulo
    - fila_encabezados
    - fila_inicio_datos
    - columnas_fechas: lista de índices columna con leyenda "Saldos s/ Balance"
    - columna_cuenta: índice columna que contiene "Cuenta"/"Descripción"
    o **None** si la tabla no se encuentra.
    """

    fila_titulo = None
    for row_idx in range(1, 30):
        for col_idx in range(1, 15):
            val = sheet.cell(row=row_idx, column=col_idx).value
            if isinstance(val, str) and (
                "SUMARIA" in val.upper() or "CEDULA" in val.upper()
            ):
                fila_titulo = row_idx
                break
        if fila_titulo:
            break

    if not fila_titulo:
        return None

    fila_encabezados = None
    for row_idx in range(fila_titulo, fila_titulo + 15):
        for col_idx in range(1, 15):
            val = sheet.cell(row=row_idx, column=col_idx).value
            if _es_encabezado_saldos(val):
                fila_encabezados = row_idx
                break
        if fila_encabezados:
            break

    if not fila_encabezados:
        return None

    columnas_fechas: List[int] = [
        col
        for col in range(1, 15)
        if _es_encabezado_saldos(sheet.cell(row=fila_encabezados, column=col).value)
    ]

    columna_cuenta = None
    for col_idx in range(1, 15):
        val = sheet.cell(row=fila_encabezados + 1, column=col_idx).value
        if isinstance(val, str) and (
            "CUENTA" in val.upper() or "DESCRIPCIÓN" in val.upper()
        ):
            columna_cuenta = col_idx
            break

    fila_inicio_datos = fila_encabezados + 2

    return {
        "fila_titulo": fila_titulo,
        "fila_encabezados": fila_encabezados,
        "fila_inicio_datos": fila_inicio_datos,
        "columnas_fechas": columnas_fechas,
        "columna_cuenta": columna_cuenta,
    }
