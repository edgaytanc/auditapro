"""
Escritor para la NUEVA plantilla 'Importancia Relativa.xlsx' (hoja '1. Datos Entrada').

A diferencia de las plantillas antiguas (hojas 'IR INGRESOS TOTALES',
'IR ACTIVOS TOTALES', 'IR UTILIDAD' con salida fija en B26/C26), la nueva
plantilla concentra los datos financieros en la hoja '1. Datos Entrada':

    A9  'Ingresos Totales (Ventas)'      → B9  (año actual) / C9  (año anterior)
    A10 'Activos Totales'                → B10 (año actual) / C10 (año anterior)
    A11 'Utilidad Antes de Impuestos'    → B11 (año actual) / C11 (año anterior)

Las filas se localizan por etiqueta (no por número fijo) para tolerar cambios
menores de la plantilla. La lógica de extracción replica la de los módulos
ingresos_totales / activos_totales / utilidad, expuesta aquí como helpers
reutilizables (también los usa el escritor de Materialidad_NIA320).
"""

import unicodedata

__all__ = [
    "process_ir_datos_entrada",
    "buscar_valor_estado_resultados",
    "calcular_ingresos_totales",
    "calcular_utilidad_antes_impuesto",
    "calcular_total_seccion",
    "obtener_anios_anuales",
]


# ---------------------------------------------------------------------
# Helpers de extracción reutilizables
# ---------------------------------------------------------------------

def _norm_texto(value):
    """Normaliza texto: sin tildes, minúsculas y sin espacios."""
    if not value:
        return ""
    value = str(value)
    value = "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )
    return value.lower().replace(" ", "").replace("\xa0", "")


def obtener_anios_anuales(balances):
    """Devuelve los años con balances ANUAL, ordenados de más reciente a más viejo."""
    anios = set()
    for key in balances.keys():
        if key.startswith('ANUAL-'):
            parts = key.split('-')
            if len(parts) > 1 and parts[1].isdigit():
                anios.add(parts[1])
    return sorted(anios, reverse=True)


# Variantes con que el Excel Financiero puede rotular cada base. Se comparan
# normalizadas (sin tildes, sin espacios, minúsculas) para que dé igual si el
# cliente escribe 'Ingresos totales', 'INGRESOS TOTALES' o 'Ingresos Totales'.
_ALIAS_BASES = {
    "Ingresos totales": (
        "ingresostotales",
        "totalingresos",
        "ingresostotalesventas",
        "ventastotales",
    ),
    "Utilidad antes de impuesto": (
        "utilidadantesdeimpuesto",
        "utilidadantesdeimpuestos",
        "utilidadantesdeimpuestosobrelarenta",
        "resultadoantesdeimpuesto",
        "resultadoantesdeimpuestos",
        "utilidadantesdeisr",
    ),
}

# Palabras que clasifican una cuenta de ESTADO DE RESULTADOS como gasto/costo
_PALABRAS_GASTO = ('gasto', 'costo', 'egreso', 'impuesto', 'perdida')
_PALABRAS_INGRESO = ('ingreso', 'venta')


def _cuenta_de_clave(key):
    """Extrae el nombre de cuenta de una clave 'TIPO-fecha-seccion-cuenta'."""
    partes = key.split('-')
    # La sección puede traer guiones ('ESTADO DE RESULTADOS' no, pero el nombre
    # de la cuenta sí), así que se corta después del marcador de sección.
    marcador = 'ESTADO DE RESULTADOS-'
    posicion = key.find(marcador)
    if posicion >= 0:
        return key[posicion + len(marcador):].strip()
    return partes[-1].strip()


def _claves_estado_resultados(balances, anio):
    """Pares (cuenta, valor) del ESTADO DE RESULTADOS anual del año dado."""
    for key, value in balances.items():
        if f"ANUAL-{anio}" in key and "ESTADO DE RESULTADOS" in key:
            yield _cuenta_de_clave(key), value


def buscar_valor_estado_resultados(balances, anio, nombre_cuenta):
    """
    Busca una cuenta de ESTADO DE RESULTADOS para un año dado.

    Acepta las variantes de rotulación del Excel Financiero (mayúsculas,
    tildes y sinónimos habituales). Devuelve el valor o None si no existe.
    """
    if anio is None:
        return None

    alias = _ALIAS_BASES.get(nombre_cuenta, ())
    objetivo = _norm_texto(nombre_cuenta)

    for cuenta, valor in _claves_estado_resultados(balances, anio):
        cuenta_norm = _norm_texto(cuenta)
        if cuenta_norm == objetivo or cuenta_norm in alias:
            return valor

    # Coincidencia parcial como último recurso (p. ej. 'Ingresos totales netos')
    for cuenta, valor in _claves_estado_resultados(balances, anio):
        cuenta_norm = _norm_texto(cuenta)
        if objetivo and (objetivo in cuenta_norm or cuenta_norm in objetivo):
            return valor
        if any(clave in cuenta_norm for clave in alias):
            return valor

    return None


def _es_cuenta_gasto(cuenta):
    texto = _norm_texto(cuenta)
    if any(palabra in texto for palabra in _PALABRAS_INGRESO):
        return False
    return any(palabra in texto for palabra in _PALABRAS_GASTO)


def _cierre_excel_financiero(audit_id):
    """
    Fecha de cierre del último Excel Financiero 2026 importado (columna H, o
    E como respaldo), o None si la auditoría se cargó con el formato clásico.
    """
    if not audit_id:
        return None
    try:
        from auditoria.services.cortes_excel import cortes_de_auditoria
        cortes = cortes_de_auditoria(audit_id)
    except Exception:
        return None
    if not cortes:
        return None
    return cortes.get('actual') or next(
        (f for f in reversed(cortes.get('cortes') or []) if f), None)


def _total_capturado_del_excel(audit_id, campo, anio):
    """
    Total 'Total Ingresos' / 'Utilidad antes de impuesto' capturado del propio
    archivo al importar (fila de total, no cuenta). Devuelve None si no hay o
    si el capturado pertenece a OTRO ejercicio (p. ej. quedó de un archivo
    anterior y luego se importó un año distinto).
    """
    if not audit_id or anio is None:
        return None

    # Guarda de frescura: el total capturado es del ejercicio del último
    # Excel Financiero importado. Para otro año no aplica.
    cierre = _cierre_excel_financiero(audit_id)
    if not cierre or str(cierre.year) != str(anio):
        return None

    try:
        from auditoria.services.cortes_excel import totales_er_de_auditoria
        ingresos, utilidad = totales_er_de_auditoria(audit_id)
    except Exception:
        return None
    return ingresos if campo == 'ingresos' else utilidad


def calcular_ingresos_totales(balances, anio, audit_id=None):
    """
    Ingresos totales del año. Prioridad (siempre trazable al archivo):

      1. La cuenta 'Ingresos totales' del ESTADO DE RESULTADOS, si existe.
      2. La fila 'Total Ingresos' que el archivo trae en sus hojas (capturada
         al importar; solo si pertenece a este mismo ejercicio).
      3. Suma de las cuentas de ingreso del ESTADO DE RESULTADOS
         (comportamiento histórico).
    """
    valor = buscar_valor_estado_resultados(balances, anio, "Ingresos totales")
    if valor is not None:
        return valor

    capturado = _total_capturado_del_excel(audit_id, 'ingresos', anio)
    if capturado is not None:
        return capturado

    total = 0
    encontrado = False
    for cuenta, importe in _claves_estado_resultados(balances, anio):
        if not _es_cuenta_gasto(cuenta) and any(
                palabra in _norm_texto(cuenta) for palabra in _PALABRAS_INGRESO):
            total += importe
            encontrado = True

    return total if encontrado else None


def _fecha_anual_mas_reciente(balances, anio):
    """Última fecha ANUAL (YYYY-MM-DD) del año dado, o None."""
    fechas = set()
    prefijo = f"ANUAL-{anio}"
    for key in balances:
        if key.startswith(prefijo):
            partes = key.split('-')
            if len(partes) >= 4:
                fechas.add('-'.join(partes[1:4]))
    return max(fechas) if fechas else None


def _claves_estado_resultados_en_fecha(balances, fecha):
    """Pares (cuenta, valor) del ESTADO DE RESULTADOS en una fecha exacta."""
    prefijo = f"ANUAL-{fecha}"
    for key, value in balances.items():
        if key.startswith(prefijo) and "ESTADO DE RESULTADOS" in key:
            yield _cuenta_de_clave(key), value


def _utilidad_desde_resultado_del_ejercicio(balances, anio, audit_id):
    """
    Deriva la utilidad antes de impuestos con la identidad contable a partir
    del 'Resultado del ejercicio' que trae el propio archivo:

        gastos en negativo:  Utilidad a. de impuestos = Resultado − impuestos
        gastos en positivo:  Utilidad a. de impuestos = Resultado + impuestos

    Solo aplica a auditorías cargadas con el Excel Financiero 2026 (cortes
    guardados y del mismo ejercicio): en archivos clásicos se conserva el
    respaldo histórico (ingresos − gastos). Usa únicamente el corte de cierre
    más reciente del año para no mezclar dos cortes del mismo ejercicio.
    """
    cierre = _cierre_excel_financiero(audit_id)
    if not cierre or str(cierre.year) != str(anio):
        return None

    fecha = _fecha_anual_mas_reciente(balances, anio)
    if not fecha:
        return None

    candidatos = []
    prefijo = f"ANUAL-{fecha}"
    for key, value in balances.items():
        if not key.startswith(prefijo):
            continue
        if 'resultadodelejercicio' in _norm_texto(_cuenta_de_clave(key)):
            candidatos.append((key, value))
    if not candidatos:
        return None
    # Si está en las dos secciones, manda la fila de Patrimonio
    resultado = next(
        (valor for clave, valor in candidatos if '-Patrimonio-' in clave),
        candidatos[0][1],
    )

    impuestos = 0
    suma_gastos = 0
    hay_gastos = False
    for cuenta, importe in _claves_estado_resultados_en_fecha(balances, fecha):
        texto = _norm_texto(cuenta)
        if 'impuesto' in texto:
            impuestos += importe
        elif _es_cuenta_gasto(cuenta):
            suma_gastos += importe
            hay_gastos = True

    # Convención de signos del archivo: si los gastos vienen en positivo,
    # la utilidad antes de impuestos es Resultado + impuestos; si vienen en
    # negativo (suma algebraica), es Resultado − impuestos.
    referencia_signo = suma_gastos if hay_gastos else impuestos
    if referencia_signo > 0:
        return resultado + impuestos
    return resultado - impuestos


def calcular_utilidad_antes_impuesto(balances, anio, audit_id=None):
    """
    Utilidad antes de impuesto del año. Prioridad (siempre trazable):

      1. La cuenta 'Utilidad antes de impuesto' del archivo, si existe.
      2. La fila de total equivalente capturada al importar (mismo ejercicio).
      3. Resultado del ejercicio (del archivo) ± cuentas de impuesto del ER
         (solo auditorías del Excel Financiero 2026).
      4. Ingresos − gastos del ESTADO DE RESULTADOS, sin impuestos
         (comportamiento histórico).
    """
    valor = buscar_valor_estado_resultados(balances, anio, "Utilidad antes de impuesto")
    if valor is not None:
        return valor

    capturado = _total_capturado_del_excel(audit_id, 'utilidad', anio)
    if capturado is not None:
        return capturado

    derivado = _utilidad_desde_resultado_del_ejercicio(balances, anio, audit_id)
    if derivado is not None:
        return derivado

    ingresos = 0
    gastos = 0
    encontrado = False
    for cuenta, importe in _claves_estado_resultados(balances, anio):
        texto = _norm_texto(cuenta)
        if 'impuesto' in texto:
            continue  # la base es ANTES de impuesto
        if _es_cuenta_gasto(cuenta):
            gastos += importe
        elif any(palabra in texto for palabra in _PALABRAS_INGRESO):
            ingresos += importe
        else:
            continue
        encontrado = True

    return ingresos - gastos if encontrado else None


def calcular_total_seccion(balances, anio, seccion):
    """
    Suma todas las cuentas de una sección (Activo, Pasivo, Patrimonio) en la
    fecha más reciente del año dado. Misma lógica que process_ir_activos_totales
    (prioridad ANUAL; si no hay, SEMESTRAL). Devuelve None si no hay cuentas.
    """
    anual_fecha = None
    semestral_fecha = None

    for key in balances.keys():
        if f"ANUAL-{anio}" in key:
            parts = key.split('-')
            if len(parts) >= 3:
                fecha = f"{parts[1]}-{parts[2]}"
                if anual_fecha is None or fecha > anual_fecha:
                    anual_fecha = fecha
        elif f"SEMESTRAL-{anio}" in key:
            parts = key.split('-')
            if len(parts) >= 3:
                fecha = f"{parts[1]}-{parts[2]}"
                if semestral_fecha is None or fecha > semestral_fecha:
                    semestral_fecha = fecha

    tipo_balance = "ANUAL" if anual_fecha else "SEMESTRAL"
    fecha_balance = anual_fecha if anual_fecha else semestral_fecha
    if not fecha_balance:
        return None

    total = 0
    encontrado = False
    for key, value in balances.items():
        if f"{tipo_balance}-{fecha_balance}" in key and f"{seccion}-" in key:
            total += value
            encontrado = True

    return total if encontrado else None


def _buscar_fila_etiqueta(sheet, texto_normalizado, max_row=40):
    """Devuelve la PRIMERA fila cuya columna A contiene la etiqueta buscada."""
    for row_idx in range(1, max_row + 1):
        valor = sheet.cell(row=row_idx, column=1).value
        if texto_normalizado in _norm_texto(valor):
            return row_idx
    return None


# ---------------------------------------------------------------------
# Escritor de la hoja '1. Datos Entrada'
# ---------------------------------------------------------------------

def process_ir_datos_entrada(sheet_name, workbook, balances, anio_actual,
                             audit_id=None):
    """
    Llena la hoja '1. Datos Entrada' de la nueva plantilla de Importancia
    Relativa con los datos del año más reciente (columna B) y, si existe un
    segundo año ANUAL, también del año anterior (columna C).

    Args:
        sheet_name: Nombre de la hoja a procesar
        workbook: Libro de Excel
        balances: Diccionario con los datos de balances (normalizados)
        anio_actual: Año más reciente identificado
        audit_id: id de la auditoría (para los totales capturados del archivo)
    """
    sheet = workbook[sheet_name]

    anios = obtener_anios_anuales(balances)
    anio_anterior = anios[1] if len(anios) > 1 else None

    # Localizar las filas de entrada por etiqueta (primera coincidencia)
    fila_ingresos = _buscar_fila_etiqueta(sheet, "ingresostotales")
    fila_activos = _buscar_fila_etiqueta(sheet, "activostotales")
    fila_utilidad = _buscar_fila_etiqueta(sheet, "utilidadantes")

    def _escribir(fila, valor_actual, valor_anterior):
        if fila is None:
            return
        # Columna B → año actual (0 si la cuenta no existe, igual que en las
        # plantillas antiguas); Columna C → año anterior solo si hay 2 años.
        sheet.cell(row=fila, column=2).value = valor_actual if valor_actual is not None else 0
        if anio_anterior is not None and valor_anterior is not None:
            sheet.cell(row=fila, column=3).value = valor_anterior

    # 1) Ingresos totales (cuenta 'Ingresos totales' de ESTADO DE RESULTADOS)
    _escribir(
        fila_ingresos,
        calcular_ingresos_totales(balances, anio_actual, audit_id=audit_id),
        calcular_ingresos_totales(balances, anio_anterior) if anio_anterior else None,
    )

    # 2) Activos totales (suma de la sección Activo en la fecha más reciente)
    _escribir(
        fila_activos,
        calcular_total_seccion(balances, anio_actual, "Activo"),
        calcular_total_seccion(balances, anio_anterior, "Activo")
        if anio_anterior else None,
    )

    # 3) Utilidad antes de impuesto (ESTADO DE RESULTADOS)
    _escribir(
        fila_utilidad,
        calcular_utilidad_antes_impuesto(balances, anio_actual, audit_id=audit_id),
        calcular_utilidad_antes_impuesto(balances, anio_anterior)
        if anio_anterior else None,
    )
