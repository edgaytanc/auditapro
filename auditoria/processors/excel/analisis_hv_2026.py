"""
Escritor de las plantillas 2026 de Análisis Financiero Preliminar:

- 1_Analisis_Horizontal.xlsx  (hojas 'Balance General' y 'Estado de Resultados')
- 2_Analisis_Vertical_.xlsx   (hojas 'Balance Comparativo' y 'Estado Resultados')

Las mismas plantillas existen en templates_base_financiera (2 PLANEACION/
4 Revision Informacion y Registros/2 Análisis Financiero Preliminar agregar)
y en templates_base_interna (3 PLANEACION/3 ANALISIS FINANCIERO), por lo que
este escritor sirve para ambos tipos de auditoría.

Llena las filas de cuentas con los datos ANUALES de BalanceCuentas:
- Con 2 años: escribe ambas columnas de año más las fórmulas de variación
  (horizontal) o porcentajes (vertical).
- Con 1 año: escribe solo la columna del año actual y deja los comparativos
  en blanco.

Se ancla en los rótulos propios de las plantillas ('Descripción', 'SUMA DEL
ACTIVO', 'PASIVO', 'TOTAL DE INGRESOS', etc.), insertando filas con estilo
clonado cuando el espacio no alcanza y reapuntando las fórmulas de suma.
"""

import re
import unicodedata

from .horizontal_vertical_analysis.utils import copiar_estilo

# Clave organizada: ANUAL-<fecha>-<seccion>-<cuenta> (fecha '2025' o '2025-12-31')
_PATRON_ANUAL = re.compile(
    r'^ANUAL-(\d{4})(?:-\d{2}-\d{2})?-'
    r'(Activo|Pasivo|Patrimonio|ESTADO DE RESULTADOS)-(.+)$'
)

# Palabras clave para clasificar cuentas del Estado de Resultados como gasto
_PALABRAS_GASTO = ('GASTO', 'COSTO', 'EGRESO', 'IMPUESTO', 'PERDIDA')
_PALABRAS_NO_GASTO = ('INGRESO', 'UTILIDAD', 'RESULTADO')


def _normalizar(texto):
    """Texto sin tildes, en minúsculas y con espacios colapsados."""
    s = unicodedata.normalize('NFD', str(texto))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.lower().split())


def _extraer_datos_anuales(balances):
    """Agrupa los balances ANUALES: {seccion: {año: {cuenta: valor}}}."""
    datos = {}
    for clave, valor in balances.items():
        m = _PATRON_ANUAL.match(clave)
        if not m:
            continue
        año, seccion, cuenta = m.groups()
        datos.setdefault(seccion, {}).setdefault(año, {})[cuenta.strip()] = valor
    return datos


def _años_disponibles(datos):
    años = set()
    for por_año in datos.values():
        años.update(por_año.keys())
    return sorted(años, reverse=True)


def _cuentas_de(datos, secciones, años):
    """Unión ordenada de cuentas de las secciones dadas en los años dados."""
    cuentas = []
    vistas = set()
    for seccion in secciones:
        por_año = datos.get(seccion, {})
        nombres = set()
        for año in años:
            nombres.update(por_año.get(año, {}).keys())
        for nombre in sorted(nombres):
            if nombre not in vistas:
                vistas.add(nombre)
                cuentas.append((seccion, nombre))
    return cuentas


def _valor(datos, seccion, año, cuenta):
    if año is None:
        return None
    return datos.get(seccion, {}).get(año, {}).get(cuenta, 0)


def _es_gasto(nombre):
    t = _normalizar(nombre).upper()
    if any(p in t for p in _PALABRAS_NO_GASTO):
        return False
    return any(p in t for p in _PALABRAS_GASTO)


def _buscar_fila(sheet, criterio, desde=1, hasta=150):
    """Primera fila cuyo texto (columna B, normalizado) cumple *criterio*."""
    for fila in range(desde, min(hasta, sheet.max_row) + 1):
        valor = sheet.cell(row=fila, column=2).value
        if isinstance(valor, str) and criterio(_normalizar(valor)):
            return fila
    return None


def _desplazar_rangos_combinados(sheet, desde_fila, cantidad):
    """
    insert_rows de openpyxl NO desplaza los rangos combinados: los que quedan
    por debajo del punto de inserción deben moverse a mano. Si no, la fila de
    suma desplazada cae dentro de un rango combinado obsoleto y su valor se
    pierde al guardar el libro.
    """
    rangos = [r for r in list(sheet.merged_cells.ranges) if r.min_row >= desde_fila]
    for rango in rangos:
        sheet.unmerge_cells(str(rango))
    for rango in rangos:
        sheet.merge_cells(
            start_row=rango.min_row + cantidad, start_column=rango.min_col,
            end_row=rango.max_row + cantidad, end_column=rango.max_col,
        )


def _asegurar_espacio(sheet, fila_inicio, fila_limite, necesarias):
    """Inserta filas antes de *fila_limite* clonando el estilo de la primera
    fila de datos. Devuelve la cantidad de filas insertadas."""
    disponibles = max(0, fila_limite - fila_inicio)
    faltantes = max(0, necesarias - disponibles)
    if faltantes:
        fila_modelo = fila_inicio
        _desplazar_rangos_combinados(sheet, fila_limite, faltantes)
        sheet.insert_rows(fila_limite, faltantes)
        for f in range(fila_limite, fila_limite + faltantes):
            for col in range(1, sheet.max_column + 1):
                copiar_estilo(
                    sheet.cell(row=fila_modelo, column=col),
                    sheet.cell(row=f, column=col),
                )
    return faltantes


def _limpiar_filas_sobrantes(sheet, desde, hasta, columnas):
    """Vacía las filas de muestra de la plantilla que no se usaron."""
    for f in range(desde, hasta):
        for col in columnas:
            sheet.cell(row=f, column=col).value = None


def _escribir_region(sheet, fila_inicio, fila_suma, cuentas, datos,
                     año_actual, año_anterior, es_vertical, fila_denominador=None):
    """
    Escribe las cuentas de una región (entre *fila_inicio* y la fila de
    suma/total), insertando filas si faltan. *fila_denominador* es la fila del
    total usado por los porcentajes verticales (por defecto la propia suma).
    Devuelve (filas_insertadas, fila_suma_final).
    """
    insertadas = _asegurar_espacio(sheet, fila_inicio, fila_suma, len(cuentas))
    fila_suma += insertadas
    if fila_denominador is None:
        fila_denominador = fila_suma

    dos_años = año_anterior is not None
    for i, (seccion, cuenta) in enumerate(cuentas):
        f = fila_inicio + i
        sheet.cell(row=f, column=2).value = cuenta
        valor_actual = _valor(datos, seccion, año_actual, cuenta)

        if es_vertical:
            # C=año anterior, E=año actual, D/F=% del total, G/H=variación
            sheet.cell(row=f, column=5).value = valor_actual
            sheet.cell(row=f, column=6).value = f'=IFERROR(E{f}/$E${fila_denominador},"-")'
            if dos_años:
                sheet.cell(row=f, column=3).value = _valor(datos, seccion, año_anterior, cuenta)
                sheet.cell(row=f, column=4).value = f'=IFERROR(C{f}/$C${fila_denominador},"-")'
                sheet.cell(row=f, column=7).value = f'=E{f}-C{f}'
                sheet.cell(row=f, column=8).value = f'=IFERROR(G{f}/C{f},"-")'
                sheet.cell(row=f, column=9).value = (
                    f'=IF(ISTEXT(H{f}),"",IF(H{f}>0.15,"🔴",IF(H{f}<-0.15,"🔴",'
                    f'IF(OR(H{f}>0.05,H{f}<-0.05),"🟡","🟢"))))'
                )
            else:
                for col in (3, 4, 7, 8, 9):
                    sheet.cell(row=f, column=col).value = None
        else:
            # C=año anterior, D=año actual, E/F=variación, G=tendencia
            sheet.cell(row=f, column=4).value = valor_actual
            if dos_años:
                sheet.cell(row=f, column=3).value = _valor(datos, seccion, año_anterior, cuenta)
                sheet.cell(row=f, column=5).value = f'=D{f}-C{f}'
                sheet.cell(row=f, column=6).value = f'=IFERROR(E{f}/C{f},"-")'
                sheet.cell(row=f, column=7).value = f'=IF(F{f}>0,"▲",IF(F{f}<0,"▼","●"))'
            else:
                for col in (3, 5, 6, 7):
                    sheet.cell(row=f, column=col).value = None

    # Vaciar filas de muestra no utilizadas
    columnas = range(2, 10) if es_vertical else range(2, 9)
    _limpiar_filas_sobrantes(sheet, fila_inicio + len(cuentas), fila_suma, columnas)

    # Reapuntar la fila de suma de la región
    if cuentas:
        ultima = fila_inicio + len(cuentas) - 1
        _escribir_suma(sheet, fila_suma, fila_inicio, ultima, es_vertical,
                       dos_años, fila_denominador)

    return insertadas, fila_suma


def _escribir_suma(sheet, fila, desde, hasta, es_vertical, dos_años, fila_denominador):
    if es_vertical:
        sheet.cell(row=fila, column=5).value = f'=SUM(E{desde}:E{hasta})'
        sheet.cell(row=fila, column=6).value = f'=IFERROR(E{fila}/$E${fila_denominador},"-")'
        if dos_años:
            sheet.cell(row=fila, column=3).value = f'=SUM(C{desde}:C{hasta})'
            sheet.cell(row=fila, column=4).value = f'=IFERROR(C{fila}/$C${fila_denominador},"-")'
            sheet.cell(row=fila, column=7).value = f'=E{fila}-C{fila}'
            sheet.cell(row=fila, column=8).value = f'=IFERROR(G{fila}/C{fila},"-")'
        else:
            for col in (3, 4, 7, 8):
                sheet.cell(row=fila, column=col).value = None
    else:
        sheet.cell(row=fila, column=4).value = f'=SUM(D{desde}:D{hasta})'
        if dos_años:
            sheet.cell(row=fila, column=3).value = f'=SUM(C{desde}:C{hasta})'
            sheet.cell(row=fila, column=5).value = f'=D{fila}-C{fila}'
            sheet.cell(row=fila, column=6).value = f'=IFERROR(E{fila}/C{fila},"-")'
        else:
            for col in (3, 5, 6):
                sheet.cell(row=fila, column=col).value = None


def _escribir_encabezado_años(sheet, fila, es_vertical, año_actual, año_anterior,
                              rotulo_anterior=None):
    """
    Rotula las columnas de año.

    *rotulo_anterior* permite nombrar la columna comparativa con el año que el
    auditor tiene configurado aunque el Excel importado todavía no traiga los
    importes de ese ejercicio (observación 1 del cliente).
    """
    col_actual = 5 if es_vertical else 4
    sheet.cell(row=fila, column=col_actual).value = f'Año {año_actual}'
    etiqueta_anterior = año_anterior or rotulo_anterior
    if etiqueta_anterior:
        sheet.cell(row=fila, column=3).value = f'Año {etiqueta_anterior}'


def _procesar_hoja_balance(sheet, datos, año_actual, año_anterior, es_vertical,
                           rotulo_anterior=None):
    años = [a for a in (año_actual, año_anterior) if a]
    fila_encabezado = _buscar_fila(sheet, lambda t: t == 'descripcion')
    if not fila_encabezado:
        return
    fila_suma_activo = _buscar_fila(
        sheet, lambda t: 'suma' in t and 'activo' in t, desde=fila_encabezado + 1)
    fila_pasivo = _buscar_fila(sheet, lambda t: t == 'pasivo', desde=fila_encabezado + 1)
    if not fila_suma_activo or not fila_pasivo:
        return
    fila_suma_pp = _buscar_fila(
        sheet, lambda t: 'suma' in t and 'pasivo' in t, desde=fila_pasivo + 1)
    if not fila_suma_pp:
        return

    cuentas_activo = _cuentas_de(datos, ['Activo'], años)
    cuentas_pp = _cuentas_de(datos, ['Pasivo', 'Patrimonio'], años)
    if not cuentas_activo and not cuentas_pp:
        return

    _escribir_encabezado_años(sheet, fila_encabezado, es_vertical, año_actual,
                              año_anterior, rotulo_anterior)

    insertadas, _ = _escribir_region(
        sheet, fila_encabezado + 1, fila_suma_activo, cuentas_activo,
        datos, año_actual, año_anterior, es_vertical)

    fila_pasivo += insertadas
    fila_suma_pp += insertadas
    _escribir_region(
        sheet, fila_pasivo + 1, fila_suma_pp, cuentas_pp,
        datos, año_actual, año_anterior, es_vertical)


def _procesar_hoja_estado_resultados(sheet, datos, año_actual, año_anterior, es_vertical,
                                     rotulo_anterior=None):
    años = [a for a in (año_actual, año_anterior) if a]
    fila_encabezado = _buscar_fila(sheet, lambda t: t == 'descripcion')
    if not fila_encabezado:
        return
    fila_total_ingresos = _buscar_fila(
        sheet, lambda t: 'total' in t and 'ingreso' in t, desde=fila_encabezado + 1)
    fila_gastos = _buscar_fila(sheet, lambda t: t == 'gastos', desde=fila_encabezado + 1)
    if not fila_total_ingresos or not fila_gastos:
        return
    fila_total_gastos = _buscar_fila(
        sheet, lambda t: 'total' in t and 'gasto' in t, desde=fila_gastos + 1)
    fila_resultado = _buscar_fila(
        sheet, lambda t: 'resultado del ejercicio' in t,
        desde=(fila_total_gastos or fila_gastos) + 1)
    if not fila_total_gastos:
        return

    cuentas_er = _cuentas_de(datos, ['ESTADO DE RESULTADOS'], años)
    if not cuentas_er:
        return
    ingresos = [c for c in cuentas_er if not _es_gasto(c[1])]
    gastos = [c for c in cuentas_er if _es_gasto(c[1])]

    _escribir_encabezado_años(sheet, fila_encabezado, es_vertical, año_actual,
                              año_anterior, rotulo_anterior)

    # Región de INGRESOS (los % verticales usan el total de ingresos)
    insertadas, fila_total_ingresos = _escribir_region(
        sheet, fila_encabezado + 1, fila_total_ingresos, ingresos,
        datos, año_actual, año_anterior, es_vertical)

    fila_gastos += insertadas
    fila_total_gastos += insertadas
    if fila_resultado:
        fila_resultado += insertadas

    # Región de GASTOS (en la plantilla vertical el denominador sigue siendo
    # el TOTAL DE INGRESOS)
    insertadas, fila_total_gastos = _escribir_region(
        sheet, fila_gastos + 1, fila_total_gastos, gastos,
        datos, año_actual, año_anterior, es_vertical,
        fila_denominador=fila_total_ingresos if es_vertical else None)

    if fila_resultado:
        fila_resultado += insertadas
        _escribir_resultado(sheet, fila_resultado, fila_total_ingresos,
                            fila_total_gastos, es_vertical, año_anterior is not None,
                            fila_total_ingresos)


def _escribir_resultado(sheet, fila, fila_ingresos, fila_gastos, es_vertical,
                        dos_años, fila_denominador):
    """RESULTADO DEL EJERCICIO = TOTAL DE INGRESOS - TOTAL DE GASTOS."""
    if es_vertical:
        sheet.cell(row=fila, column=5).value = f'=E{fila_ingresos}-E{fila_gastos}'
        sheet.cell(row=fila, column=6).value = f'=IFERROR(E{fila}/$E${fila_denominador},"-")'
        if dos_años:
            sheet.cell(row=fila, column=3).value = f'=C{fila_ingresos}-C{fila_gastos}'
            sheet.cell(row=fila, column=4).value = f'=IFERROR(C{fila}/$C${fila_denominador},"-")'
            sheet.cell(row=fila, column=7).value = f'=E{fila}-C{fila}'
            sheet.cell(row=fila, column=8).value = f'=IFERROR(G{fila}/C{fila},"-")'
        else:
            for col in (3, 4, 7, 8):
                sheet.cell(row=fila, column=col).value = None
    else:
        sheet.cell(row=fila, column=4).value = f'=D{fila_ingresos}-D{fila_gastos}'
        if dos_años:
            sheet.cell(row=fila, column=3).value = f'=C{fila_ingresos}-C{fila_gastos}'
            sheet.cell(row=fila, column=5).value = f'=D{fila}-C{fila}'
            sheet.cell(row=fila, column=6).value = f'=IFERROR(E{fila}/C{fila},"-")'
        else:
            for col in (3, 5, 6):
                sheet.cell(row=fila, column=col).value = None


def _rotulo_año_anterior(audit_id, año_actual, año_anterior):
    """
    Año con que rotular la columna comparativa cuando el Excel importado trae
    un solo ejercicio.

    SOLO se usa el año anterior que el auditor haya fijado a mano en «Años de
    la auditoría». Si no hay ninguno, se devuelve None y la columna conserva
    el rótulo genérico de la plantilla ('Año Anterior'): una auditoría de un
    solo ejercicio no debe mostrar un año inventado («si es 2025 pues 2025»).
    """
    if año_anterior or not año_actual:
        return None
    if audit_id:
        try:
            from auditoria.services.parametros_anios import anios_de_auditoria
            _, anterior_configurado = anios_de_auditoria(audit_id)
            if anterior_configurado:
                return str(anterior_configurado)
        except Exception:
            pass
    return None


def process_analisis_hv_2026(workbook, balances, file_name, audit_id=None):
    """
    Punto de entrada del escritor de Análisis Horizontal/Vertical 2026.

    Args:
        workbook: libro openpyxl de la plantilla
        balances: balances normalizados (sin sufijos de tipo_cuenta)
        file_name: nombre base del archivo (decide horizontal o vertical)
        audit_id: id de la auditoría, para rotular la columna comparativa con
            el año configurado por el auditor cuando el Excel trae un solo
            ejercicio

    Returns:
        El libro procesado (sin cambios si no hay datos ANUALES).
    """
    datos = _extraer_datos_anuales(balances)
    años = _años_disponibles(datos)
    if not años:
        return workbook

    año_actual = años[0]
    año_anterior = años[1] if len(años) > 1 else None
    es_vertical = 'VERTICAL' in file_name.upper()
    rotulo_anterior = _rotulo_año_anterior(audit_id, año_actual, año_anterior)

    for sheet in workbook.worksheets:
        titulo = sheet.title.upper()
        if 'BALANCE' in titulo:
            _procesar_hoja_balance(sheet, datos, año_actual, año_anterior,
                                   es_vertical, rotulo_anterior)
        elif 'RESULTADO' in titulo:
            _procesar_hoja_estado_resultados(sheet, datos, año_actual, año_anterior,
                                             es_vertical, rotulo_anterior)

    return workbook
