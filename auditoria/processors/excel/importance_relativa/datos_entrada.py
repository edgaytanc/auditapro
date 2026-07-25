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


def buscar_valor_estado_resultados(balances, anio, nombre_cuenta):
    """
    Busca una cuenta de ESTADO DE RESULTADOS para un año dado.
    Misma lógica de búsqueda flexible que process_ir_ingresos_totales /
    process_ir_utilidad. Devuelve el valor o None si no existe.
    """
    for key, value in balances.items():
        if (f"ANUAL-{anio}" in key and
                "ESTADO DE RESULTADOS" in key and
                nombre_cuenta in key):
            return value
    return None


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

def process_ir_datos_entrada(sheet_name, workbook, balances, anio_actual):
    """
    Llena la hoja '1. Datos Entrada' de la nueva plantilla de Importancia
    Relativa con los datos del año más reciente (columna B) y, si existe un
    segundo año ANUAL, también del año anterior (columna C).

    Args:
        sheet_name: Nombre de la hoja a procesar
        workbook: Libro de Excel
        balances: Diccionario con los datos de balances (normalizados)
        anio_actual: Año más reciente identificado
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
        buscar_valor_estado_resultados(balances, anio_actual, "Ingresos totales"),
        buscar_valor_estado_resultados(balances, anio_anterior, "Ingresos totales")
        if anio_anterior else None,
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
        buscar_valor_estado_resultados(balances, anio_actual, "Utilidad antes de impuesto"),
        buscar_valor_estado_resultados(balances, anio_anterior, "Utilidad antes de impuesto")
        if anio_anterior else None,
    )
