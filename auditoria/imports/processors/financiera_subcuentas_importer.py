# auditoria/imports/processors/financiera_subcuentas_importer.py

"""
Importador del NUEVO formato de Excel ("Revisoría 2025 con subcuentas")
para auditorías Financiera ('F') e Interna ('I').

Estructura esperada de la hoja 'ESTADOS FINANCIEROS':
    - Fechas de corte en C6, D6, E6 y H6 (texto 'Al DD/MM/YYYY' o fecha real).
    - Marcadores de sección en col A/B: 'Código+Activo', 'Código+Pasivo',
      'Código+Patrimonio' y 'Código+ESTADO DE RESULTADOS'.
    - Filas de cuenta: col A = código (entero), col B = nombre de la cuenta,
      C/D/E/H = saldos por fecha, F = Debe y G = Haber (ajustes).
    - Filas de 'TOTAL ...' se omiten.

Qué se guarda (todo con claves que las cédulas de financiera SÍ pueden leer):
    - BalanceCuentas tipo_balance='SEMESTRAL', tipo_cuenta='NT' para las 4 fechas
      → las consumen las CENTRALIZADORAS y las CÉDULAS SUMARIAS.
    - BalanceCuentas tipo_balance='ANUAL', tipo_cuenta='NT' para las fechas de
      cierre (E6 y H6) → las consumen materialidad, importancia relativa y
      análisis horizontal/vertical.
    - AjustesReclasificaciones (Debe/Haber) por cuenta con valores distintos de 0.
    - RevisoriaSubcuenta vía importar_subcuentas_estados_financieros
      (hojas 'SUBCUENTAS ACTIVO/PASIVO/PATRIMONIO/RESULTADOS').

⚠️ IMPORTANTE: tipo_cuenta SIEMPRE es 'NT' (nunca 'NT_ANT'/'NT_ACT'), porque
normalizar_balances solo elimina los sufijos -C/-NC/-NT y los escritores de
financiera no verían otras variantes.
"""

import unicodedata
from datetime import datetime, date

from audits.models import Audit
from auditoria.models import BalanceCuentas, AjustesReclasificaciones

__all__ = ["importar_formato_subcuentas", "es_formato_subcuentas"]


# ==========================================================
#  Helpers
# ==========================================================

def _norm(value):
    """Normaliza texto: sin tildes, minúsculas y sin espacios."""
    if not value:
        return ""
    value = str(value)
    value = "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )
    return value.lower().replace(" ", "").replace("\xa0", "")


def _parse_fecha(value):
    """
    Convierte celdas de fecha del nuevo formato en date (o None si no se puede).

    Acepta:
        - datetime / date reales de Excel
        - Textos 'Al DD/MM/YYYY', 'DD/MM/YYYY', 'DD-MM-YYYY', 'DD.MM.YYYY'
        - Fallback: los últimos 10 caracteres si viene texto adicional
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = str(value).strip()
    if s.lower().startswith("al "):
        s = s[3:].strip()

    formatos = ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d")
    for fmt in formatos:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Fallback: últimos 10 caracteres (por si viene con texto adicional)
    if len(s) >= 10:
        tail = s[-10:]
        for fmt in formatos:
            try:
                return datetime.strptime(tail, fmt).date()
            except ValueError:
                continue

    return None


def _parse_numero(value):
    """
    Convierte a float tolerando celdas de texto tipo '$ 274,105.37'
    o negativos entre paréntesis '(1,234.50)'. Devuelve None si no es número.
    """
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if not s:
        return None

    negativo = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace("\xa0", "").replace(" ", "").replace(",", "")
    if not s:
        return None
    try:
        numero = float(s)
    except ValueError:
        return None
    return -numero if negativo else numero


# Rótulos con que el archivo puede traer cada total del Estado de Resultados.
# Se comparan normalizados (sin tildes, sin espacios, minúsculas).
_ALIAS_TOTAL_INGRESOS = (
    "ingresostotales", "totalingresos", "totaldeingresos",
    "ingresostotalesventas", "totalingresosordinarios",
)
_ALIAS_UTILIDAD_AI = (
    "utilidadantesdeimpuesto", "utilidadantesdeimpuestos",
    "totalutilidadantesdeimpuesto", "totalutilidadantesdeimpuestos",
    "resultadoantesdeimpuesto", "resultadoantesdeimpuestos",
)


def _capturar_totales_estado_resultados(workbook, main_sheet, audit_id,
                                        anio_unico=False):
    """
    Busca 'Total Ingresos' / 'Utilidad antes de impuesto' en la hoja principal
    y en la hoja 'SUBCUENTAS RESULTADOS', y guarda el valor del CORTE ACTUAL
    en ParametrosAuditoria (None si el archivo no los trae).

    Solo cuando el archivo es de UN ejercicio (`anio_unico`) se acepta como
    respaldo la columna del cierre (E en la hoja principal, D en la de
    subcuentas): en archivos de dos años esa columna es el ejercicio anterior
    y capturarla daría una base de otro año.
    """
    from auditoria.services.cortes_excel import guardar_totales_er_desde_import

    def _valor_fila(row, indices):
        for indice in indices:
            if len(row) > indice:
                valor = _parse_numero(row[indice])
                if valor is not None:
                    return valor
        return None

    indices_principal = (7, 4) if anio_unico else (7,)
    indices_subcuentas = (6, 3) if anio_unico else (6,)

    ingresos = None
    utilidad = None

    # Hoja principal: nombre en col B, corte actual en col H.
    for row in main_sheet.iter_rows(values_only=True):
        nombre = _norm(row[1] if len(row) > 1 else None)
        if not nombre:
            continue
        if ingresos is None and nombre in _ALIAS_TOTAL_INGRESOS:
            ingresos = _valor_fila(row, indices_principal)
        if utilidad is None and nombre in _ALIAS_UTILIDAD_AI:
            utilidad = _valor_fila(row, indices_principal)

    # Hoja 'SUBCUENTAS RESULTADOS': nombre en col A, corte actual en col G.
    hoja_resultados = next(
        (workbook[name] for name in workbook.sheetnames
         if 'subcuentas' in name.lower() and 'resultados' in name.lower()),
        None,
    )
    if hoja_resultados is not None:
        for row in hoja_resultados.iter_rows(values_only=True):
            nombre = _norm(row[0] if len(row) > 0 else None)
            if not nombre:
                continue
            if ingresos is None and nombre in _ALIAS_TOTAL_INGRESOS:
                ingresos = _valor_fila(row, indices_subcuentas)
            if utilidad is None and nombre in _ALIAS_UTILIDAD_AI:
                utilidad = _valor_fila(row, indices_subcuentas)

    guardar_totales_er_desde_import(audit_id, ingresos, utilidad)


# Comienzos de las notas que el cliente escribe entre las filas de la hoja
# ('EJEMPLO PARA AGREGAR', 'El mismo nombre que tiene la cuenta en sistema'...).
# Van SIN espacios ni tildes porque se comparan contra _norm(), que los quita.
_INICIOS_ANOTACION = (
    'ejemplo', 'elmismonombre', 'lascuentas', 'nota', 'sepegaaqui',
    'lasfechascuando', 'elcodigosolo',
)


def _es_anotacion(nombre):
    """
    True si el texto de la columna B es una nota del archivo, no una cuenta.

    Solo se descartan las frases que el cliente escribe como guía en su hoja.
    El filtro decisivo es otro: una fila sin importes en ninguna columna de
    corte no se importa, venga con el nombre que venga.
    """
    texto = _norm(nombre)
    return not texto or texto.startswith(_INICIOS_ANOTACION)


def es_formato_subcuentas(sheetnames):
    """
    Detecta el NUEVO formato "Revisoría 2025 con subcuentas":
    hay una hoja cuyo nombre contiene 'estados financieros' y NO existen
    las hojas clásicas ANUAL/SEMESTRAL del importador general.
    """
    nombres = [str(name).lower() for name in sheetnames]

    tiene_estados_financieros = any("estados financieros" in name for name in nombres)
    tiene_formato_clasico = any(
        ("anual" in name and "semestral" not in name) or ("semestral" in name)
        for name in nombres
    )

    return tiene_estados_financieros and not tiene_formato_clasico


# ==========================================================
#  Importador principal del nuevo formato
# ==========================================================

def importar_formato_subcuentas(workbook, audit_id):
    """
    Procesa la hoja 'ESTADOS FINANCIEROS' del nuevo formato y persiste:
    BalanceCuentas (SEMESTRAL + ANUAL), AjustesReclasificaciones y
    RevisoriaSubcuenta (subhojas de SUBCUENTAS).

    Es idempotente: usa update_or_create con la clave natural de cada tabla,
    por lo que reimportar el mismo archivo no duplica registros.

    Args:
        workbook: libro openpyxl ya cargado (data_only=True)
        audit_id: id de la auditoría destino

    Returns:
        (success: bool, message: str)
    """
    audit_instance = Audit.objects.get(pk=audit_id)

    # 1) Localizar la hoja principal (tolerante a mayúsculas/espacios)
    sheet = next(
        (workbook[name] for name in workbook.sheetnames
         if "estados financieros" in name.lower()),
        None,
    )
    if sheet is None:
        return False, "❌ No se encontró la hoja 'ESTADOS FINANCIEROS' en el archivo."

    # 2) Fechas de corte (índices 0-based de columna → fecha)
    fechas_columnas = {
        2: _parse_fecha(sheet["C6"].value),  # Columna C (inicio año anterior)
        3: _parse_fecha(sheet["D6"].value),  # Columna D (julio año anterior)
        4: _parse_fecha(sheet["E6"].value),  # Columna E (31/12 año anterior)
        7: _parse_fecha(sheet["H6"].value),  # Columna H (31/12 año actual)
    }
    # Cortes de cierre (E y H) → balances ANUALES para los escritores de 2 años.
    # Se procesa E antes que H para que, si ambas fechas coinciden,
    # prevalezca el valor del corte actual (columna H).
    columnas_anuales = (4, 7)

    if all(fecha is None for fecha in fechas_columnas.values()):
        return False, "❌ No se pudieron leer las fechas de corte (C6, D6, E6, H6)."

    # 2.bis) Años de la auditoría: se toman del archivo y quedan disponibles
    # para los cuadros comparativos (el auditor puede corregirlos después).
    from auditoria.services.parametros_anios import actualizar_anios_desde_import
    actualizar_anios_desde_import(
        audit_id,
        fecha_cierre_anterior=fechas_columnas.get(4),  # Columna E
        fecha_cierre_actual=fechas_columnas.get(7),    # Columna H
    )

    # 2.ter) Cortes tal cual venían en el archivo (columnas C/D/E/H): los
    # escritores de centralizadoras y sumarias rotulan sus columnas con estas
    # fechas REALES en lugar de fabricar 'Al 01/01/{año}'.
    from auditoria.services.cortes_excel import guardar_cortes_desde_import
    guardar_cortes_desde_import(
        audit_id,
        fecha1=fechas_columnas.get(2),        # Columna C
        fecha2=fechas_columnas.get(3),        # Columna D
        fecha3=fechas_columnas.get(4),        # Columna E
        fecha_actual=fechas_columnas.get(7),  # Columna H
    )

    # 3) Recorrer las filas de la hoja por secciones
    current_section = None
    cuentas_importadas = 0

    for row in sheet.iter_rows(values_only=True):
        colA = row[0] if len(row) > 0 else None
        colB = row[1] if len(row) > 1 else None

        txtA = _norm(colA)
        txtB = _norm(colB)

        # --- Marcadores de sección ('Código+Activo', etc.) ---
        if ("codigo+activo" in txtA) or ("codigo+activo" in txtB):
            current_section = "Activo"
            continue
        if ("codigo+pasivo" in txtA) or ("codigo+pasivo" in txtB):
            current_section = "Pasivo"
            continue
        if ("codigo+patrimonio" in txtA) or ("codigo+patrimonio" in txtB):
            current_section = "Patrimonio"
            continue
        if ("codigo+estado" in txtA) or ("codigo+estado" in txtB):
            # Bloque ESTADO DE RESULTADOS: misma sección que usa la financiera
            current_section = "ESTADO DE RESULTADOS"
            continue

        if current_section is None:
            continue

        # Filas de totales/títulos: se ignoran.
        # ⚠️ Solo si EMPIEZAN por 'total' ('TOTAL ACTIVO', 'Total Pasivo', ...):
        # cuentas como 'Ingresos totales' contienen la palabra pero SÍ se importan.
        if txtA.startswith("total") or txtB.startswith("total"):
            continue

        # Filas de cuenta: lo que manda es el NOMBRE de la columna B.
        # El propio archivo del cliente advierte "EL CODIGO SOLO ES REFERENCIA
        # NO SE AUTOMATIZA", así que exigir un código entero en la columna A
        # dejaba fuera las cuentas que el auditor agrega a mano (p. ej.
        # 'Contratos', que trae texto en esa columna). Las filas de anotación
        # se descartan por el nombre y, sobre todo, porque no traen importes.
        nombre_cuenta = str(colB).strip() if colB not in (None, "") else ""
        if not nombre_cuenta or _es_anotacion(nombre_cuenta):
            continue

        # Sin ningún importe en las columnas de corte no es una cuenta: son las
        # notas que el cliente escribe entre las filas de la hoja.
        importes = [
            _parse_numero(row[col_idx]) if len(row) > col_idx else None
            for col_idx, fecha in fechas_columnas.items() if fecha is not None
        ]
        if all(valor is None for valor in importes):
            continue

        # 3.a) Saldos SEMESTRALES (las 4 fechas) → centralizadoras y sumarias
        for col_idx, fecha in fechas_columnas.items():
            if fecha is None:
                continue
            valor = _parse_numero(row[col_idx]) if len(row) > col_idx else None
            if valor is None:
                continue

            BalanceCuentas.objects.update_or_create(
                audit=audit_instance,
                tipo_balance="SEMESTRAL",
                fecha_corte=fecha,
                seccion=current_section,
                nombre_cuenta=nombre_cuenta,
                tipo_cuenta="NT",
                defaults={"valor": valor},
            )

        # 3.b) Saldos ANUALES (cortes de cierre E y H) → escritores de 2 años
        for col_idx in columnas_anuales:
            fecha = fechas_columnas.get(col_idx)
            if fecha is None:
                continue
            valor = _parse_numero(row[col_idx]) if len(row) > col_idx else None
            if valor is None:
                continue

            BalanceCuentas.objects.update_or_create(
                audit=audit_instance,
                tipo_balance="ANUAL",
                fecha_corte=fecha,
                seccion=current_section,
                nombre_cuenta=nombre_cuenta,
                tipo_cuenta="NT",
                defaults={"valor": valor},
            )

        # 3.c) Ajustes / Reclasificaciones (F = Debe, G = Haber)
        valor_debe = _parse_numero(row[5]) if len(row) > 5 else None
        valor_haber = _parse_numero(row[6]) if len(row) > 6 else None

        if (valor_debe not in (None, 0)) or (valor_haber not in (None, 0)):
            AjustesReclasificaciones.objects.update_or_create(
                audit=audit_instance,
                nombre_cuenta=nombre_cuenta,
                defaults={
                    "debe": valor_debe or 0,
                    "haber": valor_haber or 0,
                },
            )

        cuentas_importadas += 1

    if cuentas_importadas == 0:
        return False, "❌ La hoja 'ESTADOS FINANCIEROS' no contiene cuentas válidas."

    # 4) Subcuentas (hojas 'SUBCUENTAS ...') → RevisoriaSubcuenta
    # Import local para evitar el import circular con estados_financieros_importer.
    from auditoria.imports.estados_financieros_importer import (
        importar_subcuentas_estados_financieros,
    )
    importar_subcuentas_estados_financieros(audit_id, workbook)

    # 5) Totales del Estado de Resultados ('Total Ingresos', 'Utilidad antes
    # de impuesto'): el archivo los trae como filas de total, no como cuentas,
    # así que se capturan aparte para Materialidad / Importancia Relativa.
    fecha_cierre = fechas_columnas.get(4)
    fecha_actual = fechas_columnas.get(7)
    anio_unico = (
        fecha_actual is None
        or (fecha_cierre is not None and fecha_cierre.year == fecha_actual.year)
    )
    _capturar_totales_estado_resultados(workbook, sheet, audit_id,
                                        anio_unico=anio_unico)

    return True, (
        f"✅ Importación del formato con subcuentas completada "
        f"({cuentas_importadas} cuentas procesadas)."
    )
