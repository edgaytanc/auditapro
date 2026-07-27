"""
Detección del layout real de una cédula sumaria.

Las plantillas oficiales 2026 no comparten una única cuadrícula: la sumaria de
Caja y Bancos y las «OTRAS CÉDULAS SUMARIAS» traen el encabezado en la fila 7
con las fechas en la 8, mientras que la de Cuentas por Cobrar concentra todo
en una sola fila. Escribir en celdas fijas (B13/E13/F13…) descuadraba los
datos, así que aquí se localizan las columnas por su rótulo.

Una hoja se considera «cédula sumaria clásica» —y por tanto rellenable con los
saldos del Excel Financiero— sólo si tiene:

    · una columna de cuenta ('Cuenta', 'Cuenta Contable', 'Descripción'…),
    · al menos dos columnas de saldo rotuladas con fecha, y
    · el par de columnas de ajustes Debe / Haber.

Las sumarias especializadas (Patrimonio, Activos Fijos, Inversiones,
Inventarios, Construcciones, Intangible, Cuentas por Pagar, Préstamos y Estado
de Resultados) son análisis con columnas propias —'Saldo inicial', 'Adiciones',
'Categoría', 'Institución'…— que no corresponden a los cortes del balance. Para
esas, `detectar_layout` devuelve None y la hoja se deja intacta: se les pegan
igualmente el encabezado, los datos del auditor y la referencia.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

from openpyxl.worksheet.worksheet import Worksheet

__all__ = ['detectar_layout', 'LayoutSumaria']

FILAS_BUSQUEDA = 25
COLUMNAS_BUSQUEDA = 20

# Rótulos que identifican la columna de cuenta
_ETIQUETAS_CUENTA = (
    'cuenta contable',
    'cuenta / componente',
    'cuenta/componente',
    'nombre de la cuenta',
    'descripcion de la cuenta',
    'cuenta',
    'descripcion',
    'componente',
)

_ETIQUETAS_REF = ('ref. pt', 'ref p/t', 'ref.p/t', 'ref pt', 'ref. p/t', 'ref')
_ETIQUETAS_CODIGO = ('codigo', 'cod.', 'cod')
_ETIQUETAS_DEBE = ('debe', 'debito', 'cargo')
_ETIQUETAS_HABER = ('haber', 'credito', 'abono')

_PATRON_FECHA_TEXTO = re.compile(r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})')
_PATRON_TOTAL = re.compile(r'^\s*(total|suma|sumas)\b', re.IGNORECASE)


def _norm(valor):
    """Texto sin tildes, en minúsculas, con saltos de línea y espacios colapsados."""
    if valor is None:
        return ''
    texto = unicodedata.normalize('NFD', str(valor))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.replace('\n', ' ').lower().split())


def _es_fecha(valor):
    """True si la celda representa una fecha (real o rotulada 'Al dd/mm/aaaa')."""
    if isinstance(valor, (datetime, date)):
        return True
    if not isinstance(valor, str):
        return False
    return bool(_PATRON_FECHA_TEXTO.search(valor))


def _coincide(etiqueta, opciones):
    """True si *etiqueta* empieza por o contiene alguna de las *opciones*."""
    if not etiqueta:
        return False
    return any(etiqueta == opcion or etiqueta.startswith(opcion) for opcion in opciones)


class LayoutSumaria:
    """Coordenadas de la cuadrícula de una cédula sumaria."""

    def __init__(self, hoja, fila_encabezado, fila_rotulos_fecha, fila_datos,
                 fila_total, col_numero, col_codigo, col_cuenta, col_ref,
                 cols_saldo, col_debe, col_haber, col_auditado):
        self.hoja = hoja
        self.fila_encabezado = fila_encabezado
        self.fila_rotulos_fecha = fila_rotulos_fecha
        self.fila_datos = fila_datos
        self.fila_total = fila_total
        self.col_numero = col_numero
        self.col_codigo = col_codigo
        self.col_cuenta = col_cuenta
        self.col_ref = col_ref
        self.cols_saldo = cols_saldo          # columnas de corte, de izq. a der.
        self.col_debe = col_debe
        self.col_haber = col_haber
        self.col_auditado = col_auditado      # 'Saldo según auditoría', si existe

    @property
    def filas_disponibles(self):
        """Filas de datos que trae la plantilla antes del total."""
        if self.fila_total:
            return max(0, self.fila_total - self.fila_datos)
        return 0

    def __repr__(self):
        return (
            f'<LayoutSumaria hoja={self.hoja.title!r} enc={self.fila_encabezado} '
            f'datos={self.fila_datos} total={self.fila_total} '
            f'cuenta=col{self.col_cuenta} saldos={self.cols_saldo} '
            f'debe={self.col_debe} haber={self.col_haber}>'
        )


def _buscar_columna_cuenta(hoja):
    """Devuelve (fila, columna) del rótulo de la columna de cuenta."""
    mejor = None
    for fila in range(1, min(hoja.max_row, FILAS_BUSQUEDA) + 1):
        for columna in range(1, min(hoja.max_column, COLUMNAS_BUSQUEDA) + 1):
            etiqueta = _norm(hoja.cell(row=fila, column=columna).value)
            if not etiqueta:
                continue
            for prioridad, opcion in enumerate(_ETIQUETAS_CUENTA):
                if etiqueta == opcion or etiqueta.startswith(opcion):
                    # Las etiquetas más específicas ganan ('cuenta contable'
                    # antes que el genérico 'cuenta')
                    if mejor is None or prioridad < mejor[0]:
                        mejor = (prioridad, fila, columna)
                    break
        if mejor and mejor[0] == 0:
            break
    return (mejor[1], mejor[2]) if mejor else (None, None)


def _etiquetas_de_columna(hoja, fila_encabezado, columna):
    """Rótulo de grupo (fila del encabezado) y de detalle (fila siguiente)."""
    grupo = hoja.cell(row=fila_encabezado, column=columna).value
    detalle = hoja.cell(row=fila_encabezado + 1, column=columna).value
    return grupo, detalle


def _localizar_fila_datos(hoja, desde, col_numero, col_cuenta):
    """
    Primera fila de datos: la que abre la numeración correlativa o, en su
    defecto, la primera fila con contenido bajo el encabezado.
    """
    for fila in range(desde, min(hoja.max_row, desde + 8) + 1):
        if col_numero:
            valor = hoja.cell(row=fila, column=col_numero).value
            if isinstance(valor, int) or (
                    isinstance(valor, str) and valor.strip().isdigit()):
                return fila
        if hoja.cell(row=fila, column=col_cuenta).value not in (None, ''):
            return fila
    return desde


def _localizar_fila_total(hoja, desde, columnas):
    """Fila de totales (la que empieza por 'TOTAL' o 'SUMA') bajo los datos."""
    for fila in range(desde, min(hoja.max_row, desde + 80) + 1):
        for columna in columnas:
            valor = hoja.cell(row=fila, column=columna).value
            if isinstance(valor, str) and _PATRON_TOTAL.match(valor):
                return fila
    return None


def detectar_layout(hoja: Worksheet):
    """
    Devuelve un `LayoutSumaria` si *hoja* es una cédula sumaria clásica,
    o None si su cuadrícula no corresponde a los cortes del balance.
    """
    fila_encabezado, col_cuenta = _buscar_columna_cuenta(hoja)
    if not col_cuenta:
        return None

    cols_saldo = []
    col_debe = col_haber = col_ref = col_codigo = col_numero = None
    usa_fila_detalle = False

    for columna in range(1, min(hoja.max_column, COLUMNAS_BUSQUEDA) + 1):
        grupo, detalle = _etiquetas_de_columna(hoja, fila_encabezado, columna)
        etiqueta_grupo = _norm(grupo)
        etiqueta_detalle = _norm(detalle)

        if columna == col_cuenta:
            continue

        # Columnas de saldo: el rótulo (o el de la fila de detalle) es una fecha
        if _es_fecha(grupo):
            cols_saldo.append(columna)
            continue
        if _es_fecha(detalle):
            cols_saldo.append(columna)
            usa_fila_detalle = True
            continue

        if _coincide(etiqueta_grupo, _ETIQUETAS_DEBE) or _coincide(etiqueta_detalle, _ETIQUETAS_DEBE):
            col_debe = columna
        elif _coincide(etiqueta_grupo, _ETIQUETAS_HABER) or _coincide(etiqueta_detalle, _ETIQUETAS_HABER):
            col_haber = columna
        elif col_ref is None and (_coincide(etiqueta_grupo, _ETIQUETAS_REF)
                                  or _coincide(etiqueta_detalle, _ETIQUETAS_REF)):
            col_ref = columna
        elif col_codigo is None and (_coincide(etiqueta_grupo, _ETIQUETAS_CODIGO)
                                     or _coincide(etiqueta_detalle, _ETIQUETAS_CODIGO)):
            col_codigo = columna
        elif col_numero is None and etiqueta_grupo in ('no.', 'no', 'n.', 'n', '#', 'num.', 'numero'):
            col_numero = columna

    # Guardas: sin dos cortes rotulados con fecha y sin el par Debe/Haber la
    # hoja es un análisis propio del área, no una sumaria de saldos.
    if len(cols_saldo) < 2 or col_debe is None or col_haber is None:
        return None

    # La última columna de saldo suele ser 'Saldo según auditoría'
    col_auditado = cols_saldo[-1] if len(cols_saldo) > 2 and cols_saldo[-1] > col_haber else None
    cols_corte = [c for c in cols_saldo if c != col_auditado]

    fila_rotulos_fecha = fila_encabezado + 1 if usa_fila_detalle else fila_encabezado
    fila_datos = _localizar_fila_datos(hoja, fila_rotulos_fecha + 1, col_numero, col_cuenta)
    columnas_total = [c for c in (col_numero, col_codigo, col_cuenta) if c]
    fila_total = _localizar_fila_total(hoja, fila_datos, columnas_total or [1])

    return LayoutSumaria(
        hoja=hoja,
        fila_encabezado=fila_encabezado,
        fila_rotulos_fecha=fila_rotulos_fecha,
        fila_datos=fila_datos,
        fila_total=fila_total,
        col_numero=col_numero,
        col_codigo=col_codigo,
        col_cuenta=col_cuenta,
        col_ref=col_ref,
        cols_saldo=cols_corte,
        col_debe=col_debe,
        col_haber=col_haber,
        col_auditado=col_auditado,
    )
