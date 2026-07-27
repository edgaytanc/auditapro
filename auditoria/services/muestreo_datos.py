"""
Lectura en memoria del Excel de datos ("mayor auxiliar") para Muestreo NIA 530.

El archivo del cliente NUNCA se almacena: se recibe el objeto subido, se parsea
en memoria con openpyxl, se derivan los parámetros (N, sigma, BV) y las
partidas reales, y el archivo se descarta al terminar la petición.

Formato esperado (modelo entregado al cliente):
    - Hoja 'Mayor Auxiliar' (si no existe, se usa la primera hoja).
    - Metadatos en la columna A de las primeras filas:
          'Empresa: X' / 'Auditoría: Y' / 'Cuenta: Z'   (tolerante a faltantes)
    - Fila de encabezados (se detecta dinámicamente en las filas 1-15):
          A = 'N.º Documento' · B = 'Descripción' · C = 'Fecha' · D = 'Monto'
    - Partidas a continuación del encabezado, hasta la primera fila vacía.

Los errores de formato se lanzan como ValueError con mensaje en español.
"""

import bisect
import math
import re
import unicodedata
from datetime import date, datetime

from openpyxl import load_workbook

NOMBRE_HOJA_ESPERADA = 'Mayor Auxiliar'
MAX_PARTIDAS = 20000
FILAS_BUSQUEDA_ENCABEZADO = 15
REGEX_METADATO = re.compile(r'^(Empresa|Auditor[íi]a|Cuenta):\s*(.*)$', re.IGNORECASE)


def _normalizar(texto):
    """Minúsculas y sin acentos, para detectar encabezados con tolerancia."""
    if texto is None:
        return ''
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = ''.join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return texto.strip().lower()


def _celda_vacia(valor):
    """True si la celda no aporta contenido (None o texto en blanco)."""
    return valor is None or (isinstance(valor, str) and valor.strip() == '')


def _fecha_iso(valor):
    """Convierte la celda de fecha a texto ISO (YYYY-MM-DD); tolera texto libre."""
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if valor is None:
        return ''
    return str(valor).strip()


def _monto_float(valor, numero_fila):
    """Convierte la celda de monto a float o lanza ValueError en español."""
    if isinstance(valor, bool) or valor is None:
        raise ValueError(
            f"La fila {numero_fila} no tiene un monto numérico en la columna D (Monto). "
            "Revise el archivo contra el modelo de mayor auxiliar."
        )
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        return float(str(valor).strip().replace(',', ''))
    except (TypeError, ValueError):
        raise ValueError(
            f"La fila {numero_fila} no tiene un monto numérico en la columna D (Monto). "
            "Revise el archivo contra el modelo de mayor auxiliar."
        )


def parsear_mayor_auxiliar(archivo):
    """
    Parsea el Excel del mayor auxiliar EN MEMORIA (no se guarda en disco).

    Devuelve:
        {
            'empresa': str, 'auditoria': str, 'cuenta': str,
            'n': int,          # cantidad de partidas
            'sigma': float,    # desviación estándar poblacional de Monto
            'bv': float,       # suma de Monto (valor en libros)
            'partidas': [ {'no', 'documento', 'descripcion', 'fecha', 'monto'}, ... ],
        }

    Lanza ValueError con mensaje en español si el formato no es válido.
    """
    try:
        libro = load_workbook(archivo, read_only=True, data_only=True)
    except Exception:
        raise ValueError(
            "El archivo no es un Excel válido (.xlsx). "
            "Descargue el mayor auxiliar de ejemplo y use ese formato."
        )

    try:
        # Hoja 'Mayor Auxiliar' o, en su defecto, la primera hoja del libro
        if NOMBRE_HOJA_ESPERADA in libro.sheetnames:
            hoja = libro[NOMBRE_HOJA_ESPERADA]
        else:
            hoja = libro[libro.sheetnames[0]]

        metadatos = {'empresa': '', 'auditoria': '', 'cuenta': ''}
        fila_encabezado = None
        partidas = []

        for numero_fila, fila in enumerate(
                hoja.iter_rows(min_col=1, max_col=4, values_only=True), start=1):
            celda_a, celda_b, celda_c, celda_d = fila

            if fila_encabezado is None:
                if numero_fila > FILAS_BUSQUEDA_ENCABEZADO:
                    break

                # Metadatos 'Empresa: X' / 'Auditoría: Y' / 'Cuenta: Z' en la columna A
                if isinstance(celda_a, str):
                    coincidencia = REGEX_METADATO.match(celda_a.strip())
                    if coincidencia:
                        clave = _normalizar(coincidencia.group(1))  # empresa | auditoria | cuenta
                        if clave in metadatos:
                            metadatos[clave] = coincidencia.group(2).strip()
                        continue

                # Detección dinámica del encabezado: A contiene 'documento' y D 'monto'
                if 'documento' in _normalizar(celda_a) and 'monto' in _normalizar(celda_d):
                    fila_encabezado = numero_fila
                continue

            # Zona de datos: termina en la primera fila totalmente vacía
            if all(_celda_vacia(valor) for valor in (celda_a, celda_b, celda_c, celda_d)):
                break

            if len(partidas) >= MAX_PARTIDAS:
                raise ValueError(
                    f"El archivo excede el máximo de {MAX_PARTIDAS:,} partidas soportadas. "
                    "Divida el mayor auxiliar en archivos más pequeños."
                )

            partidas.append({
                'no': len(partidas) + 1,
                'documento': '' if celda_a is None else str(celda_a).strip(),
                'descripcion': '' if celda_b is None else str(celda_b).strip(),
                'fecha': _fecha_iso(celda_c),
                'monto': _monto_float(celda_d, numero_fila),
            })
    finally:
        libro.close()

    if fila_encabezado is None:
        raise ValueError(
            "No se encontró la fila de encabezados (columnas 'N.º Documento' y 'Monto') "
            f"en las primeras {FILAS_BUSQUEDA_ENCABEZADO} filas. "
            "Descargue el mayor auxiliar de ejemplo y use ese formato."
        )
    if not partidas:
        raise ValueError(
            "El archivo no contiene partidas debajo de la fila de encabezados. "
            "Verifique que los movimientos estén registrados a partir de la fila siguiente al encabezado."
        )

    montos = [partida['monto'] for partida in partidas]
    n = len(montos)
    bv = math.fsum(montos)
    media = bv / n
    sigma = math.sqrt(math.fsum((monto - media) ** 2 for monto in montos) / n)

    return {
        'empresa': metadatos['empresa'],
        'auditoria': metadatos['auditoria'],
        'cuenta': metadatos['cuenta'],
        'n': n,
        'sigma': sigma,
        'bv': bv,
        'partidas': partidas,
    }


# ---------------------------------------------------------------------------
# Mapeo de la selección estadística a las partidas reales del archivo
# ---------------------------------------------------------------------------

def _mapear_por_indice(resultado, partidas):
    """Métodos por índice (aleatorio simple, estratificado, atributos)."""
    detalle = []
    for item in resultado['seleccion']:
        indice = item.get('indice')
        if indice is None:
            return None  # selección sin índice (p. ej. criterio): sin mapeo
        if indice > len(partidas):
            raise ValueError(
                f"La selección incluye la partida {indice}, pero el archivo importado "
                f"solo tiene {len(partidas)} partidas. Ajuste la población (N) al número "
                "de filas del mayor auxiliar."
            )
        partida = partidas[indice - 1]
        detalle.append({
            'no': item['numero'],
            'documento': partida['documento'],
            'descripcion': partida['descripcion'],
            'fecha': partida['fecha'],
            'monto': partida['monto'],
        })
    return detalle


def _mapear_mus(resultado, partidas):
    """
    Selección MUS clásica: cada punto monetario cae en la partida cuyo rango
    acumulado de Monto lo contiene (cum_{j-1} < punto <= cum_j).
    """
    acumulados = []
    total = 0.0
    for partida in partidas:
        if partida['monto'] < 0:
            raise ValueError(
                "El muestreo monetario (MUS) requiere montos no negativos: la partida "
                f"{partida['no']} ({partida['documento']}) tiene monto negativo. "
                "Depure el mayor auxiliar o use otro método."
            )
        total += partida['monto']
        acumulados.append(total)

    if total <= 0:
        raise ValueError("El mayor auxiliar no tiene montos positivos: el MUS no es aplicable.")

    detalle = []
    for item in resultado['seleccion']:
        punto = item.get('punto')
        if punto is None:
            return None
        posicion = bisect.bisect_left(acumulados, punto)
        if posicion >= len(partidas):
            posicion = len(partidas) - 1  # borde: BV indicado mayor que la suma real
        partida = partidas[posicion]
        detalle.append({
            'no': item['numero'],
            'documento': partida['documento'],
            'descripcion': partida['descripcion'],
            'fecha': partida['fecha'],
            'monto': partida['monto'],
        })
    return detalle


def mapear_seleccion_a_partidas(resultado, partidas):
    """
    Convierte la selección del servicio de muestreo en filas con las partidas
    REALES del archivo importado. Devuelve None cuando el mapeo no aplica
    (método por criterio o selección sin índices), para que el papel de trabajo
    se genere igual que en el modo manual.
    """
    if not partidas:
        return None
    if resultado.get('metodo') == 'mus':
        return _mapear_mus(resultado, partidas)
    if resultado.get('metodo') == 'criterio':
        return None
    return _mapear_por_indice(resultado, partidas)


# ---------------------------------------------------------------------------
# Parámetros derivados del archivo
# ---------------------------------------------------------------------------

# Qué parámetro de cada método se puede deducir del mayor auxiliar importado.
#   poblacion → número de partidas
#   sigma     → desviación estándar de los montos
#   valor_libros → suma de los montos
PARAMETROS_DERIVABLES = {
    'aleatorio_simple': {'poblacion': 'n', 'sigma': 'sigma'},
    'estratificado': {'sigma': 'sigma'},
    'mus': {'valor_libros': 'bv'},
    'atributos': {'poblacion': 'n'},
    'criterio': {},
}


def _sin_valor(valor):
    """True si el auditor dejó el parámetro vacío en el formulario."""
    return valor is None or (isinstance(valor, str) and valor.strip() == '')


def completar_parametros(metodo, parametros, datos_archivo):
    """
    Rellena con los datos del archivo los parámetros que el auditor dejó vacíos.

    Lo que el auditor sí escribió manda: el archivo solo cubre los huecos, de
    modo que pueda ajustar la población o la desviación si tiene un criterio
    profesional distinto.
    """
    completados = dict(parametros or {})
    for parametro, clave_archivo in PARAMETROS_DERIVABLES.get(metodo, {}).items():
        if _sin_valor(completados.get(parametro)):
            completados[parametro] = datos_archivo[clave_archivo]
    return completados


# ---------------------------------------------------------------------------
# Archivo de ejemplo con la estructura esperada
# ---------------------------------------------------------------------------

COLUMNAS_FORMATO = ('N.º Documento', 'Descripción', 'Fecha', 'Monto (Q)')

_INSTRUCCIONES = (
    ('Cómo usar este archivo', ''),
    ('1.', 'Sustituya las filas de ejemplo por los movimientos del mayor auxiliar '
           'de la cuenta que va a muestrear.'),
    ('2.', 'Respete la fila de encabezados: N.º Documento · Descripción · Fecha · Monto. '
           'El orden de las columnas no debe cambiar.'),
    ('3.', 'Los metadatos Empresa / Auditoría / Cuenta son opcionales, pero ayudan a '
           'identificar el papel de trabajo.'),
    ('4.', 'No deje filas en blanco entre partidas: la primera fila vacía marca el '
           'final de los datos.'),
    ('5.', 'En el módulo de Muestreo NIA 530 elija el método, suba este archivo y el '
           'sistema calculará la muestra automáticamente.'),
    ('Importante', 'El archivo NO se guarda en el sistema: se lee, se genera la muestra '
                   'y se descarta. Para volver a generarla, súbalo de nuevo.'),
    ('Se deduce del archivo', 'Población (N) = número de partidas · Desviación estándar (σ) '
                              'y Valor en libros = calculados sobre la columna Monto.'),
)

_EJEMPLO = (
    ('DOC-3512', 'Venta a crédito - Comercial Guatemalteca, S.A.', '26/05/2024', 72299.42),
    ('DOC-3513', 'Venta a crédito - Comercializadora Maya, S.A.', '29/10/2024', 86236.56),
    ('DOC-3514', 'Nota de crédito - Grupo Xela, S.A.', '14/10/2024', 3383.15),
    ('DOC-3515', 'Anticipo de cliente - Suministros Industriales, S.A.', '22/05/2024', 166698.31),
    ('DOC-3516', 'Cobro parcial - Almacenes Vega, S.A.', '22/05/2024', 2754.45),
)


def generar_formato_ejemplo():
    """
    Devuelve (en bytes) el Excel de ejemplo con la estructura que espera el
    módulo de Muestreo, más una hoja de instrucciones.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    encabezado_fuente = Font(bold=True, color='FFFFFF')
    encabezado_fondo = PatternFill('solid', fgColor='1F6F43')

    libro = Workbook()

    hoja = libro.active
    hoja.title = 'Mayor Auxiliar'
    hoja['A1'] = 'Empresa: Empresa ABC, S.A.'
    hoja['A2'] = 'Auditoría: Auditoría Financiera 2025'
    hoja['A3'] = 'Cuenta: 1305 - Cuentas por Cobrar Comerciales'

    fila_encabezado = 6
    for indice, titulo in enumerate(COLUMNAS_FORMATO, start=1):
        celda = hoja.cell(row=fila_encabezado, column=indice, value=titulo)
        celda.font = encabezado_fuente
        celda.fill = encabezado_fondo
        celda.alignment = Alignment(horizontal='center')

    for desplazamiento, partida in enumerate(_EJEMPLO, start=1):
        for columna, valor in enumerate(partida, start=1):
            hoja.cell(row=fila_encabezado + desplazamiento, column=columna, value=valor)

    for columna, ancho in zip('ABCD', (18, 52, 14, 16)):
        hoja.column_dimensions[columna].width = ancho

    instrucciones = libro.create_sheet('Instrucciones')
    instrucciones.column_dimensions['A'].width = 24
    instrucciones.column_dimensions['B'].width = 95
    for fila, (titulo, texto) in enumerate(_INSTRUCCIONES, start=1):
        celda_titulo = instrucciones.cell(row=fila, column=1, value=titulo)
        celda_titulo.font = Font(bold=True)
        celda_titulo.alignment = Alignment(vertical='top')
        celda_texto = instrucciones.cell(row=fila, column=2, value=texto)
        celda_texto.alignment = Alignment(wrap_text=True, vertical='top')

    import io as _io
    buffer = _io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
