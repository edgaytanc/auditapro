"""
Escritura de cuentas y saldos en una cédula sumaria usando su layout real.

Sustituye a la escritura en celdas fijas (B13, E13, F13…) de `insercion.py`,
que descuadraba los datos en las plantillas oficiales 2026. Aquí todo se
escribe respecto de las coordenadas que devuelve `layout.detectar_layout`.
"""

from __future__ import annotations

from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from .fechas import _formatear_fecha_ddmmaa
from .data_extraction import encontrar_ajuste_para_cuenta
from .formulas import ajustar_formula_para_nueva_fila

__all__ = ['escribir_sumaria']


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


def _actualizar_rotulos_fecha(layout, fechas_ordenadas):
    """Rotula las columnas de corte con las fechas reales del Excel importado."""
    hoja = layout.hoja
    fila = layout.fila_rotulos_fecha

    for indice, columna in enumerate(layout.cols_saldo):
        if indice >= len(fechas_ordenadas):
            break
        etiqueta = _formatear_fecha_ddmmaa(fechas_ordenadas[indice])
        celda = hoja.cell(row=fila, column=columna)
        anterior = celda.value
        # Se conserva el prefijo 'Al ' cuando la plantilla ya lo traía
        if isinstance(anterior, str) and anterior.strip().lower().startswith('al '):
            celda.value = f'Al {etiqueta}'
        else:
            celda.value = f'Al {etiqueta}'
        celda.alignment = Alignment(horizontal='center', wrap_text=True)

    if layout.col_auditado and fechas_ordenadas:
        celda = hoja.cell(row=fila, column=layout.col_auditado)
        celda.value = f'Al {_formatear_fecha_ddmmaa(fechas_ordenadas[-1])}'
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


def escribir_sumaria(layout, cuentas, fechas_ordenadas, ajustes_reclasificaciones,
                     referencias_por_cuenta=None):
    """
    Escribe las cuentas del Excel Financiero en la cédula sumaria.

    Args:
        layout: `LayoutSumaria` de la hoja
        cuentas: {nombre_cuenta: {fecha: importe}}
        fechas_ordenadas: cortes del balance, de más antiguo a más reciente
        ajustes_reclasificaciones: {cuenta: {'debe': x, 'haber': y}}
        referencias_por_cuenta: {cuenta: 'A-1'} para la columna Ref P/T

    Returns:
        Cantidad de cuentas escritas.
    """
    if not cuentas:
        return 0

    hoja = layout.hoja
    nombres = sorted(cuentas)
    _asegurar_filas(layout, len(nombres))
    _actualizar_rotulos_fecha(layout, fechas_ordenadas)

    referencias_por_cuenta = referencias_por_cuenta or {}

    for indice, nombre in enumerate(nombres):
        fila = layout.fila_datos + indice

        if layout.col_numero:
            hoja.cell(row=fila, column=layout.col_numero).value = indice + 1
        hoja.cell(row=fila, column=layout.col_cuenta).value = nombre

        if layout.col_ref:
            referencia = referencias_por_cuenta.get(nombre)
            hoja.cell(row=fila, column=layout.col_ref).value = referencia or ''

        for posicion, columna in enumerate(layout.cols_saldo):
            if posicion >= len(fechas_ordenadas):
                break
            importe = cuentas[nombre].get(fechas_ordenadas[posicion])
            if importe is None:
                continue
            celda = hoja.cell(row=fila, column=columna)
            celda.value = importe
            celda.alignment = Alignment(horizontal='right')

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
                ultimo = layout.cols_saldo[-1] if layout.cols_saldo else None
                if ultimo:
                    letra_saldo = get_column_letter(ultimo)
                    letra_debe = get_column_letter(layout.col_debe)
                    letra_haber = get_column_letter(layout.col_haber)
                    celda.value = (
                        f'=IFERROR({letra_saldo}{fila}+{letra_debe}{fila}'
                        f'-{letra_haber}{fila},"")'
                    )

    # Vaciar las filas de muestra sobrantes de la plantilla
    ultima_escrita = layout.fila_datos + len(nombres) - 1
    if layout.fila_total:
        for fila in range(ultima_escrita + 1, layout.fila_total):
            _limpiar_fila(layout, fila)

    _actualizar_totales(layout, layout.fila_datos, ultima_escrita)

    return len(nombres)
