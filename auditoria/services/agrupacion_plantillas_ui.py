"""Agrupa solo para la visualización los documentos repetidos conocidos.

Se selecciona una única plantilla existente en el catálogo de producción.
NO se modifican los JSON ni se eliminan los archivos Word/Excel; las demás
variantes permanecen en su ruta para los servicios que las utilicen.
"""
from __future__ import annotations

import re
import json
from functools import lru_cache
from pathlib import Path


def _norm(ruta):
    return (ruta or "").replace("\\", "/").strip("/")


def clave_grupo_visual(nombre, carpeta, tipo):
    """Clave específica por tipo y carpeta; no agrupa cédulas por similitud."""
    carpeta = _norm(carpeta)
    tipo = (tipo or "").upper()
    stem, dot, ext = nombre.rpartition(".")
    ext = ext.lower()
    if not dot or ext not in {"xlsx", "xlsm", "xls", "docx", "doc"}:
        return None

    # Fase inicial: se conserva la plantilla base original de producción
    # (primera entrada de su grupo, según el orden del JSON).
    if tipo == "F" and carpeta == "1 FASE INICIAL" and ext == "xlsx":
        m = re.match(r"^(\d{1,2})\s+", nombre)
        if m and 1 <= int(m.group(1)) <= 15:
            return ("fase-inicial", int(m.group(1)), ext)

    # Pareja idéntica: se prioriza el nombre corregido que ya existe en
    # producción. Se mantiene intacta la ruta real de descarga.
    if tipo == "F" and carpeta == "2 PLANEACION/1 Reunion Preliminar y Solicitud":
        if nombre in {
            "2.1 Control Solicitud de Inforamacion.xlsx",
            "2.1 Control Solicitud de Informacion.xlsx",
        }:
            return ("control-solicitud", ext)

    if tipo == "F" and carpeta == "2 PLANEACION/4 Revision Informacion y Registros/2 Análisis Financiero Preliminar agregar":
        if nombre in {"1_Analisis_Horizontal.xlsx", "1_Analisis_Horizontal_1.xlsx"}:
            return ("financiera-analisis-horizontal", ext)
        if nombre in {"2_Analisis_Vertical_.xlsx", "2_Analisis_Vertical_1_1.xlsx"}:
            return ("financiera-analisis-vertical", ext)

    if tipo == "I" and carpeta == "3 PLANEACION/3 ANALISIS FINANCIERO":
        if nombre in {"1_Analisis_Horizontal.xlsx", "1_Analisis_Horizontal_1.xlsx"}:
            return ("interna-analisis-horizontal", ext)
        if nombre in {"2_Analisis_Vertical.xlsx", "2_Analisis_Vertical_1_1.xlsx"}:
            return ("interna-analisis-vertical", ext)

    if tipo == "R" and carpeta == "3 PRUEBAS DETECCIÓN DE FRAUDES":
        if nombre in {
            "2 Deteccion Fraudes Cuentas por Cobrar.xlsx",
            "2 Deteccion_Fraudes_Cuentas por Cobrar.xlsx",
        }:
            return ("revisoria-fraude-cxc", ext)
    return None


def etiqueta_visual(nombre):
    """Elimina solo prefijos numéricos generados; mantiene el archivo real."""
    return re.sub(r"^\d{11,}_(?=\d+[_ ])", "", nombre)


def agrupar_entradas(estructura, carpeta, tipo):
    """Entrega solo (nombre, contenido) del documento principal del grupo.

    La estructura original NO se modifica; se filtra solamente el árbol HTML.
    Las carpetas y las cédulas con referencias distintas se mantienen.
    """
    grupos = {}
    resultado = []
    for nombre, contenido in estructura.items():
        if isinstance(contenido, dict):
            resultado.append((nombre, contenido))
            continue
        key = clave_grupo_visual(nombre, carpeta, tipo)
        if key is None:
            resultado.append((nombre, contenido))
            continue
        if key not in grupos:
            grupos[key] = len(resultado)
            resultado.append((nombre, contenido))
        elif (key[0] == "control-solicitud" and
              nombre == "2.1 Control Solicitud de Informacion.xlsx"):
            # El documento corregido también está en el catálogo productivo.
            resultado[grupos[key]] = (nombre, contenido)
    return resultado


# Catálogo visual oficial: procede del ZIP productivo entregado. Solo decide
# qué archivos/carpetas se VEN, no toca el JSON operativo ni las plantillas
# físicas, referencias manuales o servicios de descarga.
_CATALOGO_PRODUCTIVO = {"F": "financiera", "I": "interna", "R": "revisoria"}


@lru_cache(maxsize=3)
def _rutas_visibles_productivo(tipo):
    nombre = _CATALOGO_PRODUCTIVO.get((tipo or "").upper())
    if not nombre:
        return None
    ruta = Path(__file__).resolve().parents[1] / "config" / f"catalogo_ui_productivo_{nombre}.json"
    if not ruta.is_file():
        return None
    with ruta.open(encoding="utf-8") as archivo:
        return frozenset(json.load(archivo))


def _ruta_equivalente_productivo(ruta):
    """Corrige solo diferencias de *ruta de catálogo*, nunca el archivo."""
    return (
        _norm(ruta)
        .replace("2 Análisis Financiero Preliminar agregar", "2 Análisis Financiero Preliminar")
        .replace("CENTRALIZADORA  DEL", "CENTRALIZADORA DEL")
    )


def filtrar_estructura_visible_productivo(estructura, tipo):
    """Muestra el inventario productivo sin borrar nada ni modificar la entrada.

    Es deliberadamente un filtro del árbol de la página de detalle: el JSON
    actual sigue siendo el utilizado por descargas, referencias y automatizaciones.
    En caso de no contar con inventario, devuelve el árbol original.
    """
    permitidos = _rutas_visibles_productivo(tipo)
    if permitidos is None or not isinstance(estructura, dict):
        return estructura

    def recorrer(nodo, prefijo=""):
        salida = {}
        for nombre, contenido in nodo.items():
            ruta = f"{prefijo}/{nombre}" if prefijo else nombre
            if isinstance(contenido, dict):
                descendientes = recorrer(contenido, ruta)
                if descendientes:
                    salida[nombre] = descendientes
            elif _ruta_equivalente_productivo(ruta) in permitidos:
                salida[nombre] = contenido
        return salida

    return recorrer(estructura)


def ruta_es_productiva(tipo, ruta):
    """Para listados del modal: no impide una descarga por ruta ya conocida."""
    permitidos = _rutas_visibles_productivo(tipo)
    return permitidos is None or _ruta_equivalente_productivo(ruta) in permitidos


def carpeta_es_productiva(tipo, carpeta):
    """Devuelve True si esta carpeta contiene algún documento oficial."""
    permitidos = _rutas_visibles_productivo(tipo)
    if permitidos is None:
        return True
    prefijo = _ruta_equivalente_productivo(carpeta).rstrip('/') + '/'
    return any(r.startswith(prefijo) for r in permitidos)
