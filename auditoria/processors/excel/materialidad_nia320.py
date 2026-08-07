"""
Escritor para la NUEVA plantilla 'Materialidad_NIA320.xlsx'.

La lógica antigua de process_materialidad_file (ancla 'Base de materialidad',
cuenta en col B y valor en col D) NO aplica a esta plantilla: la hoja
'Entrada de Datos' trae BASES FIJAS con el monto en la columna B y fórmulas
en la columna D que no deben pisarse:

    A15 'Utilidad antes de impuestos' → B15 (monto)
    A16 'Activos totales'             → B16 (monto)
    A17 'Ingresos totales'            → B17 (monto)
    A18 'Patrimonio'                  → B18 (monto)

Este módulo llena SOLO la columna B de esas bases con los datos del año más
reciente, reutilizando los helpers de extracción del paquete de Importancia
Relativa. No modifica process_materialidad_file (plantillas antiguas).
"""

from .importance_relativa.datos_entrada import (
    _norm_texto,
    obtener_anios_anuales,
    calcular_ingresos_totales,
    calcular_utilidad_antes_impuesto,
    calcular_total_seccion,
)

__all__ = ["process_materialidad_nia320"]


def process_materialidad_nia320(workbook, balances, audit_id=None):
    """
    Procesa la nueva plantilla de materialidad (NIA 320) llenando la hoja
    'Entrada de Datos' con las bases del año más reciente.

    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros (normalizados)
        audit_id: id de la auditoría (para los totales capturados del archivo)

    Returns:
        El libro de Excel procesado
    """
    anios = obtener_anios_anuales(balances)
    if not anios:
        return workbook

    anio_actual = anios[0]

    # Localizar la hoja de entrada de datos (tolerante a mayúsculas)
    sheet = next(
        (workbook[name] for name in workbook.sheetnames
         if "entrada de datos" in name.lower()),
        None,
    )
    if sheet is None:
        return workbook

    # Valores de las bases (0 si la cuenta no existe, como en los escritores IR)
    valores_bases = {
        "utilidadantesdeimpuestos": calcular_utilidad_antes_impuesto(
            balances, anio_actual, audit_id=audit_id),
        "activostotales": calcular_total_seccion(balances, anio_actual, "Activo"),
        "ingresostotales": calcular_ingresos_totales(
            balances, anio_actual, audit_id=audit_id),
        "patrimonio": calcular_total_seccion(balances, anio_actual, "Patrimonio"),
    }

    # Escribir el monto (col B) en la fila de cada base, localizada por etiqueta
    # EXACTA en la columna A para no tocar encabezados ni otras secciones.
    filas_bases = {}
    for row_idx in range(1, min(sheet.max_row, 60) + 1):
        etiqueta = _norm_texto(sheet.cell(row=row_idx, column=1).value)
        if etiqueta in valores_bases:
            valor = valores_bases.pop(etiqueta)
            sheet.cell(row=row_idx, column=2).value = valor if valor is not None else 0
            filas_bases[etiqueta] = row_idx
        if not valores_bases:
            break

    _reparar_hoja_calculo(workbook, sheet.title, filas_bases)

    return workbook


def _reparar_hoja_calculo(workbook, nombre_hoja_entrada, filas_bases):
    """
    La hoja 'Cálculo Materialidad' de la plantilla oficial trae la fila de
    'Utilidad antes de impuestos' con constantes de muestra (monto 8 y 10 %)
    en lugar de enlazar a la hoja de entrada, como sí hacen las otras bases.
    Aquí se repara: toda fila de base cuyo monto/porcentaje no sea fórmula se
    enlaza a su fila de 'Entrada de Datos'.
    """
    hoja_calculo = next(
        (workbook[name] for name in workbook.sheetnames
         if "calculo" in _norm_texto(name) and "materialidad" in _norm_texto(name)),
        None,
    )
    if hoja_calculo is None or not filas_bases:
        return

    for row_idx in range(1, min(hoja_calculo.max_row, 60) + 1):
        etiqueta = _norm_texto(hoja_calculo.cell(row=row_idx, column=1).value)
        fila_entrada = filas_bases.get(etiqueta)
        if not fila_entrada:
            continue
        for columna in (2, 3):  # B = monto, C = porcentaje
            celda = hoja_calculo.cell(row=row_idx, column=columna)
            if isinstance(celda.value, str) and celda.value.startswith('='):
                continue  # ya enlaza a la entrada; no se toca
            celda.value = (
                f"='{nombre_hoja_entrada}'!{'B' if columna == 2 else 'C'}{fila_entrada}"
            )
