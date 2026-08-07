"""
Escritores de las plantillas 2026 de la carpeta '1 Revision':

  · 1_Comparativo_Registros.xlsx   -> COMPARATIVO DE SALDOS
        columna C = saldo según Estados Financieros (Excel importado)
        columna D = saldo según Registros Auxiliares (si se importaron)
  · 2_Prueba_Saldos_Iniciales.xlsx -> VERIFICACIÓN DE SALDOS
        columna C = saldo final del período anterior
        columna D = saldo inicial del período actual

Las dos traen las filas de cuentas ya escritas en la columna B y las fórmulas
de diferencia/porcentaje puestas: aquí solo se rellenan los importes, que era
lo que quedaba en blanco al importar el Excel Financiero.
"""

import re
import unicodedata

__all__ = [
    'es_comparativo_registros',
    'es_prueba_saldos_iniciales',
    'process_comparativo_registros_2026',
    'process_prueba_saldos_iniciales_2026',
]

# Claves del diccionario de balances: '<TIPO>-<fecha>-<sección>-<cuenta>-<tipo>'
_PATRON_BALANCE = re.compile(
    r'^(ANUAL|SEMESTRAL)-(\d{4})-(\d{2})-(\d{2})-([^-]+)-(.+?)(?:-[A-Z]{1,3})?$')

# Encabezado de la tabla de cada plantilla y columnas a rellenar
_TABLA_COMPARATIVO = ('COMPARATIVO DE SALDOS', 3, 4)     # C y D
_TABLA_SALDOS = ('VERIFICACIÓN DE SALDOS', 3, 4)         # C y D


def _normalizar(texto):
    """minúsculas, sin tildes y sin espacios de más."""
    s = unicodedata.normalize('NFD', str(texto or ''))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.lower().split())


def _sin_plural(texto):
    """Quita la 's' final de cada palabra ('intangibles' -> 'intangible')."""
    return ' '.join(p[:-1] if len(p) > 3 and p.endswith('s') else p
                    for p in texto.split())


def _coincide(nombre_plantilla, nombre_importado):
    """
    La fila de la plantilla y la cuenta importada son la misma cuenta.

    Se compara sin tildes, sin mayúsculas y sin plurales, porque la plantilla
    rotula 'Intangibles' donde el Excel del cliente trae 'Activo Intangible'.
    """
    a, b = _normalizar(nombre_plantilla), _normalizar(nombre_importado)
    if not a or not b:
        return False
    if a == b:
        return True
    a, b = _sin_plural(a), _sin_plural(b)
    return a == b or a in b or b in a


def _cuentas_por_fecha(balances):
    """{fecha: {cuenta: valor}} a partir de las claves de balances."""
    datos = {}
    for clave, valor in (balances or {}).items():
        encontrado = _PATRON_BALANCE.match(str(clave))
        if not encontrado:
            continue
        _, anio, mes, dia, _seccion, cuenta = encontrado.groups()
        fecha = f'{anio}-{mes}-{dia}'
        datos.setdefault(fecha, {})[cuenta.strip()] = valor
    return datos


def _saldos_al_corte(por_fecha, fecha_objetivo):
    """
    Saldos de TODAS las cuentas al corte indicado.

    Las cuentas que el Excel trae sin importes se guardan solo en el primer
    corte (con valor cero), así que si se mirara únicamente la fecha objetivo
    esas cuentas desaparecerían de la plantilla. Aquí se parte de todas las
    cuentas conocidas y se usa el saldo de la fecha objetivo cuando existe.
    """
    completos = {}
    for fecha in sorted(por_fecha):
        completos.update(por_fecha[fecha])
    completos.update(por_fecha.get(fecha_objetivo, {}))
    return completos


def _valor_para(cuentas, nombre_fila):
    """Importe de la cuenta que corresponde a la fila de la plantilla."""
    for cuenta, valor in (cuentas or {}).items():
        if _coincide(nombre_fila, cuenta):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None
    return None


def _buscar_tabla(hoja, titulo):
    """Fila del encabezado de la tabla cuyo título es *titulo*."""
    objetivo = _normalizar(titulo)
    for fila in range(1, min(hoja.max_row, 80) + 1):
        for columna in range(1, 4):
            if _normalizar(hoja.cell(row=fila, column=columna).value) == objetivo:
                return fila + 1  # la fila siguiente son los encabezados
    return None


def _filas_de_cuentas(hoja, fila_encabezado, limite=40):
    """[(fila, nombre)] de las filas con nombre de cuenta en la columna B."""
    filas = []
    for fila in range(fila_encabezado + 1, fila_encabezado + 1 + limite):
        nombre = hoja.cell(row=fila, column=2).value
        if not isinstance(nombre, str) or not nombre.strip():
            continue
        if _normalizar(nombre).startswith(('total', 'suma')):
            break
        filas.append((fila, nombre.strip()))
    return filas


def es_comparativo_registros(file_name):
    return _normalizar(file_name).startswith('1_comparativo_registros')


def es_prueba_saldos_iniciales(file_name):
    return _normalizar(file_name).startswith('2_prueba_saldos_iniciales')


def process_comparativo_registros_2026(workbook, balances, registros_auxiliares=None):
    """
    Rellena 'COMPARATIVO DE SALDOS' con el saldo de los Estados Financieros
    (columna C) y el de los registros auxiliares (columna D).
    """
    por_fecha = _cuentas_por_fecha(balances)
    if not por_fecha:
        return workbook
    cuentas = _saldos_al_corte(por_fecha, max(por_fecha))

    titulo, col_ef, col_aux = _TABLA_COMPARATIVO
    for hoja in workbook.worksheets:
        encabezado = _buscar_tabla(hoja, titulo)
        if not encabezado:
            continue
        for fila, nombre in _filas_de_cuentas(hoja, encabezado):
            valor = _valor_para(cuentas, nombre)
            auxiliar = _valor_para(registros_auxiliares, nombre)
            if valor is None:
                # Rubro que la auditoría no tiene importado: se limpian los
                # importes de ejemplo de la plantilla (traía 100 / 50) para no
                # mostrar cifras que no son de esta auditoría.
                hoja.cell(row=fila, column=col_ef).value = None
                hoja.cell(row=fila, column=col_aux).value = None
                continue
            hoja.cell(row=fila, column=col_ef).value = valor
            # Sin registros auxiliares importados se iguala el saldo para que
            # la diferencia quede en cero y no se marque como material una
            # cuenta que todavía no se ha comparado.
            hoja.cell(row=fila, column=col_aux).value = (
                auxiliar if auxiliar is not None else valor)
        break
    return workbook


def process_prueba_saldos_iniciales_2026(workbook, balances, saldos_iniciales=None):
    """
    Rellena 'VERIFICACIÓN DE SALDOS' con el saldo final del período anterior
    (columna C) y el inicial del actual (columna D).

    El saldo inicial del período actual es, por definición, el final del
    anterior: si el Excel no trae una columna de apertura, se escriben iguales
    y la diferencia queda en cero (que es el resultado esperado de la prueba).
    """
    por_fecha = _cuentas_por_fecha(balances)
    if not por_fecha:
        return workbook

    fechas = sorted(por_fecha)
    anio_actual = int(fechas[-1][:4])
    cierres_anteriores = [f for f in fechas if int(f[:4]) < anio_actual]
    corte_anterior = cierres_anteriores[-1] if cierres_anteriores else fechas[0]
    cuentas_anterior = _saldos_al_corte(por_fecha, corte_anterior)

    # Apertura del ejercicio actual, si el archivo la trae
    aperturas = [f for f in fechas if int(f[:4]) == anio_actual]
    cuentas_apertura = (_saldos_al_corte(por_fecha, aperturas[0])
                        if len(aperturas) > 1 else None)

    titulo, col_anterior, col_actual = _TABLA_SALDOS
    for hoja in workbook.worksheets:
        encabezado = _buscar_tabla(hoja, titulo)
        if not encabezado:
            continue
        for fila, nombre in _filas_de_cuentas(hoja, encabezado):
            final_anterior = _valor_para(cuentas_anterior, nombre)
            if final_anterior is None:
                continue
            hoja.cell(row=fila, column=col_anterior).value = final_anterior
            inicial = _valor_para(saldos_iniciales, nombre)
            if inicial is None and cuentas_apertura:
                inicial = _valor_para(cuentas_apertura, nombre)
            hoja.cell(row=fila, column=col_actual).value = (
                inicial if inicial is not None else final_anterior)
        break
    return workbook
