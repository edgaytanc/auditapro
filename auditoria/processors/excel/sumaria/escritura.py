"""
Escritura de cuentas y saldos en una cédula sumaria usando su layout real.

Sustituye a la escritura en celdas fijas (B13, E13, F13…) de `insercion.py`,
que descuadraba los datos en las plantillas oficiales 2026. Aquí todo se
escribe respecto de las coordenadas que devuelve `layout.detectar_layout`.
"""

from __future__ import annotations

import re
import unicodedata

from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from .fechas import _formatear_fecha_ddmmaa
from .data_extraction import encontrar_ajuste_para_cuenta
from .formulas import ajustar_formula_para_nueva_fila, desplazar_referencias_de_fila

__all__ = ['escribir_sumaria']

# Hueco del título de la plantilla: 'CÉDULA SUMARIA — XXXXXXXXX'
_PATRON_TITULO_HUECO = re.compile(r'X{3,}')


def _copiar_estilo(origen, destino):
    destino.font = origen.font.copy()
    destino.border = origen.border.copy()
    destino.fill = origen.fill.copy()
    destino.number_format = origen.number_format
    destino.alignment = origen.alignment.copy()
    destino.protection = origen.protection.copy()


def _clonar_fila_modelo(hoja, fila_modelo, fila_destino, max_columna):
    """Replica estilos y fórmulas de la fila modelo en una fila nueva."""
    for columna in range(1, max_columna + 1):
        celda_origen = hoja.cell(row=fila_modelo, column=columna)
        celda_destino = hoja.cell(row=fila_destino, column=columna)
        _copiar_estilo(celda_origen, celda_destino)
        if isinstance(celda_origen.value, str) and celda_origen.value.startswith('='):
            celda_destino.value = ajustar_formula_para_nueva_fila(
                celda_origen.value, fila_modelo, fila_destino
            )


def _asegurar_filas(layout, necesarias):
    """
    Inserta filas antes del total si la plantilla no trae suficientes.
    Devuelve la cantidad insertada.
    """
    hoja = layout.hoja
    if not layout.fila_total:
        return 0

    faltantes = max(0, necesarias - layout.filas_disponibles)
    if not faltantes:
        return 0

    fila_modelo = layout.fila_datos
    max_columna = min(hoja.max_column, 20)
    fila_insercion = layout.fila_total

    # insert_rows no desplaza los rangos combinados que quedan por debajo
    rangos = [r for r in list(hoja.merged_cells.ranges) if r.min_row >= layout.fila_total]
    for rango in rangos:
        hoja.unmerge_cells(str(rango))

    hoja.insert_rows(layout.fila_total, faltantes)

    for rango in rangos:
        hoja.merge_cells(
            start_row=rango.min_row + faltantes, start_column=rango.min_col,
            end_row=rango.max_row + faltantes, end_column=rango.max_col,
        )

    # insert_rows tampoco traduce las fórmulas que quedaron debajo de la
    # inserción (p. ej. el bloque 'VERIFICACIÓN DE DIFERENCIAS' que apunta a
    # la fila de totales): se desplazan aquí sus referencias.
    for fila in range(fila_insercion + faltantes, hoja.max_row + 1):
        for columna in range(1, max_columna + 1):
            celda = hoja.cell(row=fila, column=columna)
            if isinstance(celda, MergedCell):
                continue
            if isinstance(celda.value, str) and celda.value.startswith('='):
                celda.value = desplazar_referencias_de_fila(
                    celda.value, fila_insercion, faltantes)

    for desplazamiento in range(faltantes):
        _clonar_fila_modelo(hoja, fila_modelo, layout.fila_total + desplazamiento, max_columna)

    layout.fila_total += faltantes
    return faltantes


def _limpiar_fila(layout, fila):
    """Vacía una fila de muestra que no se usó (sin tocar sus fórmulas)."""
    columnas = [layout.col_codigo, layout.col_cuenta, layout.col_ref,
                layout.col_debe, layout.col_haber]
    columnas.extend(layout.cols_saldo)
    for columna in columnas:
        if not columna:
            continue
        celda = layout.hoja.cell(row=fila, column=columna)
        if isinstance(celda.value, str) and celda.value.startswith('='):
            continue
        celda.value = None


def _norm_texto_titulo(valor):
    """Texto sin tildes y en minúsculas, para localizar el título de la cédula."""
    if valor is None:
        return ''
    texto = unicodedata.normalize('NFD', str(valor))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto.lower()


def _reemplazar_titulo(hoja, titulo):
    """
    Sustituye el hueco 'XXXXXXXXX' del título ('CÉDULA SUMARIA — XXXXXXXXX')
    por el nombre del área, en las primeras filas de la hoja.
    """
    if not titulo:
        return
    for fila in range(1, 13):
        for columna in range(1, 16):
            celda = hoja.cell(row=fila, column=columna)
            if isinstance(celda, MergedCell):
                continue
            valor = celda.value
            if not isinstance(valor, str):
                continue
            if 'sumaria' in _norm_texto_titulo(valor) and _PATRON_TITULO_HUECO.search(valor):
                celda.value = _PATRON_TITULO_HUECO.sub(titulo.upper(), valor)
                return


def _fechas_por_columna(layout, fechas_ordenadas, cortes):
    """
    Asigna una fecha (ISO) a cada columna de corte y al 'Saldo según auditoría'.

    Con `cortes` del Excel Financiero 2026, cada columna recibe SU corte del
    archivo (C→1.ª, D→2.ª, E→3.ª) aunque algún corte venga vacío, y el saldo
    según auditoría usa el corte del año actual (columna H del archivo). Sin
    cortes guardados se mantiene el comportamiento clásico (fechas en orden).

    Returns:
        (pares, fecha_auditado): pares = [(columna, fecha_iso | None), ...]
    """
    if cortes:
        fechas_archivo = [
            fecha.isoformat() if fecha else None
            for fecha in (cortes.get('cortes') or [])
        ]
        pares = list(zip(layout.cols_saldo, fechas_archivo))
        actual = cortes.get('actual') or next(
            (f for f in reversed(cortes.get('cortes') or []) if f), None)
        fecha_auditado = actual.isoformat() if actual else (
            fechas_ordenadas[-1] if fechas_ordenadas else None)
        return pares, fecha_auditado

    pares = [
        (columna, fechas_ordenadas[indice] if indice < len(fechas_ordenadas) else None)
        for indice, columna in enumerate(layout.cols_saldo)
    ]
    fecha_auditado = fechas_ordenadas[-1] if fechas_ordenadas else None
    return pares, fecha_auditado


def _actualizar_rotulos_fecha(layout, pares, fecha_auditado, limpiar_vacios=False):
    """Rotula las columnas de corte con las fechas reales del Excel importado."""
    hoja = layout.hoja
    fila = layout.fila_rotulos_fecha

    for columna, fecha in pares:
        celda = hoja.cell(row=fila, column=columna)
        if not fecha:
            # Modo cortes: el archivo no trae este corte; se limpia el rótulo
            # de muestra de la plantilla para no mostrar una fecha ajena.
            if limpiar_vacios and not isinstance(celda, MergedCell):
                celda.value = None
            continue
        etiqueta = _formatear_fecha_ddmmaa(fecha)
        celda.value = f'Al {etiqueta}'
        celda.alignment = Alignment(horizontal='center', wrap_text=True)

    if layout.col_auditado and fecha_auditado:
        celda = hoja.cell(row=fila, column=layout.col_auditado)
        celda.value = f'Al {_formatear_fecha_ddmmaa(fecha_auditado)}'
        celda.alignment = Alignment(horizontal='center', wrap_text=True)


def _actualizar_totales(layout, primera_fila, ultima_fila):
    """Reapunta las fórmulas de la fila de totales al rango escrito."""
    if not layout.fila_total or ultima_fila < primera_fila:
        return

    columnas = list(layout.cols_saldo)
    for columna in (layout.col_debe, layout.col_haber, layout.col_auditado):
        if columna:
            columnas.append(columna)

    for columna in columnas:
        letra = get_column_letter(columna)
        layout.hoja.cell(row=layout.fila_total, column=columna).value = (
            f'=SUM({letra}{primera_fila}:{letra}{ultima_fila})'
        )


def _formula_auditado(layout, fila):
    """Fórmula 'Saldo según auditoría' = último corte ± ajustes."""
    ultimo = layout.cols_saldo[-1] if layout.cols_saldo else None
    if not ultimo:
        return None
    letra_saldo = get_column_letter(ultimo)
    letra_debe = get_column_letter(layout.col_debe)
    letra_haber = get_column_letter(layout.col_haber)
    return f'=IFERROR({letra_saldo}{fila}+{letra_debe}{fila}-{letra_haber}{fila},"")'


def _numero(valor):
    """Decimal/str → float para que Excel lo trate como número."""
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _fila_fuera_de_cuadricula(layout, fila):
    """
    True si `fila` ya no pertenece a la cuadrícula de datos (celda de cuenta
    combinada: se llegó al bloque de totales/pie). Protege contra plantillas
    cuya fila de totales no se pudo detectar.
    """
    celda = layout.hoja.cell(row=fila, column=layout.col_cuenta)
    return isinstance(celda, MergedCell)


def _escribir_fila_saldos(layout, fila, pares, importes_por_fecha, limpiar_vacios=False):
    """
    Escribe los importes de una fila, cada corte en SU columna.

    Con `limpiar_vacios` (modo cortes del Excel Financiero 2026), los cortes
    sin importe VACÍAN la celda para no dejar los valores de muestra de la
    plantilla junto a las cuentas reales.
    """
    for columna, fecha in pares:
        importe = importes_por_fecha.get(fecha) if fecha else None
        celda = layout.hoja.cell(row=fila, column=columna)
        if importe is None:
            if limpiar_vacios and not (
                    isinstance(celda.value, str) and celda.value.startswith('=')):
                celda.value = None
            continue
        celda.value = importe
        celda.alignment = Alignment(horizontal='right')


def _cerrar_cuadricula(layout, filas_escritas):
    """Limpia filas de muestra sobrantes y reapunta la fila de totales."""
    ultima_escrita = layout.fila_datos + filas_escritas - 1
    if layout.fila_total:
        for fila in range(ultima_escrita + 1, layout.fila_total):
            _limpiar_fila(layout, fila)
    _actualizar_totales(layout, layout.fila_datos, ultima_escrita)


def _escribir_filas_subcuentas(layout, subcuentas, pares, fecha_auditado):
    """
    Escribe las subcuentas del Excel del cliente como filas de detalle,
    igual que las cédulas de Revisoría: tres cortes en sus columnas,
    ajustes Debe/Haber y saldo del año actual en 'Saldo según auditoría'.
    """
    hoja = layout.hoja
    columnas_corte = [columna for columna, _ in pares] or list(layout.cols_saldo)

    escritas = 0
    for indice, subcuenta in enumerate(subcuentas):
        fila = layout.fila_datos + indice

        # Protección: si la plantilla se quedó sin filas de cuadrícula (no se
        # detectó su fila de totales), no se escribe encima del pie de página.
        if _fila_fuera_de_cuadricula(layout, fila):
            break

        if layout.col_numero:
            hoja.cell(row=fila, column=layout.col_numero).value = indice + 1
        hoja.cell(row=fila, column=layout.col_cuenta).value = subcuenta.nombre_subcuenta

        if layout.col_ref:
            hoja.cell(row=fila, column=layout.col_ref).value = ''

        saldos = (
            _numero(subcuenta.saldo_ini_anterior),
            _numero(subcuenta.saldo_julio_anterior),
            _numero(subcuenta.saldo_dic_anterior),
        )
        for columna, saldo in zip(columnas_corte, saldos):
            celda = hoja.cell(row=fila, column=columna)
            if saldo is None:
                # No dejar valores de muestra de la plantilla en filas usadas
                if not (isinstance(celda.value, str) and celda.value.startswith('=')):
                    celda.value = None
                continue
            celda.value = saldo
            celda.alignment = Alignment(horizontal='right')

        if layout.col_debe:
            hoja.cell(row=fila, column=layout.col_debe).value = (
                _numero(subcuenta.ajuste_debe) or 0)
        if layout.col_haber:
            hoja.cell(row=fila, column=layout.col_haber).value = (
                _numero(subcuenta.ajuste_haber) or 0)

        if layout.col_auditado:
            celda = hoja.cell(row=fila, column=layout.col_auditado)
            if not (isinstance(celda.value, str) and celda.value.startswith('=')):
                formula = _formula_auditado(layout, fila)
                saldo_actual = _numero(subcuenta.saldo_dic_actual)
                celda.value = formula if formula else saldo_actual

        escritas += 1

    return escritas


def escribir_sumaria(layout, cuentas, fechas_ordenadas, ajustes_reclasificaciones,
                     referencias_por_cuenta=None, cortes=None, subcuentas=None,
                     titulo=None):
    """
    Escribe las cuentas del Excel Financiero en la cédula sumaria.

    Args:
        layout: `LayoutSumaria` de la hoja
        cuentas: {nombre_cuenta: {fecha: importe}}
        fechas_ordenadas: cortes del balance, de más antiguo a más reciente
        ajustes_reclasificaciones: {cuenta: {'debe': x, 'haber': y}}
        referencias_por_cuenta: {cuenta: 'A-1'} para la columna Ref P/T
        cortes: cortes reales del Excel importado (cortes_de_auditoria) o None
        subcuentas: filas RevisoriaSubcuenta del área; si vienen, la cédula
            lista ese detalle (igual que Revisoría) en lugar de una sola fila
        titulo: nombre del área para el hueco 'CÉDULA SUMARIA — XXXXXXXXX'

    Returns:
        Cantidad de filas escritas.
    """
    subcuentas = list(subcuentas or [])
    if not cuentas and not subcuentas:
        return 0

    hoja = layout.hoja
    _reemplazar_titulo(hoja, titulo)

    modo_cortes = bool(cortes)
    pares, fecha_auditado = _fechas_por_columna(layout, fechas_ordenadas, cortes)
    _actualizar_rotulos_fecha(layout, pares, fecha_auditado, limpiar_vacios=modo_cortes)

    # Detalle de subcuentas del cliente (espejo de las cédulas de Revisoría)
    if subcuentas:
        _asegurar_filas(layout, len(subcuentas))
        escritas = _escribir_filas_subcuentas(layout, subcuentas, pares, fecha_auditado)
        _cerrar_cuadricula(layout, escritas)
        return escritas

    nombres = sorted(cuentas)
    _asegurar_filas(layout, len(nombres))

    referencias_por_cuenta = referencias_por_cuenta or {}

    escritas = 0
    for indice, nombre in enumerate(nombres):
        fila = layout.fila_datos + indice

        # Protección: no escribir encima del pie si la plantilla se quedó sin
        # filas de cuadrícula (fila de totales no detectada).
        if _fila_fuera_de_cuadricula(layout, fila):
            break

        if layout.col_numero:
            hoja.cell(row=fila, column=layout.col_numero).value = indice + 1
        hoja.cell(row=fila, column=layout.col_cuenta).value = nombre

        if layout.col_ref:
            referencia = referencias_por_cuenta.get(nombre)
            hoja.cell(row=fila, column=layout.col_ref).value = referencia or ''

        _escribir_fila_saldos(layout, fila, pares, cuentas[nombre],
                              limpiar_vacios=modo_cortes)

        ajuste = encontrar_ajuste_para_cuenta(ajustes_reclasificaciones, nombre) or {}
        if layout.col_debe:
            hoja.cell(row=fila, column=layout.col_debe).value = ajuste.get('debe', 0)
        if layout.col_haber:
            hoja.cell(row=fila, column=layout.col_haber).value = ajuste.get('haber', 0)

        # 'Saldo según auditoría' = último corte ± ajustes, si la plantilla no
        # trae ya su propia fórmula en esa celda.
        if layout.col_auditado:
            celda = hoja.cell(row=fila, column=layout.col_auditado)
            if not (isinstance(celda.value, str) and celda.value.startswith('=')):
                formula = _formula_auditado(layout, fila)
                if formula:
                    celda.value = formula

        escritas += 1

    _cerrar_cuadricula(layout, escritas)

    return escritas
