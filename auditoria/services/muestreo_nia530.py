"""
Servicio de cálculo de muestreo estadístico según NIA 530.

Funciones puras (sin dependencias de Django) que calculan el tamaño de muestra
y la selección de elementos para los cinco métodos aprobados en el mockup:

    1. Aleatorio Simple
    2. Estratificado
    3. Monetario (MUS)
    4. Por Atributos
    5. Por Criterio (selección dirigida, no estadística)

Cada función devuelve un diccionario con la misma estructura:
    {
        'metodo': str,            # clave interna del método
        'metodo_nombre': str,     # nombre para mostrar
        'nia_ref': 'NIA 530',
        'parametros': {...},      # parámetros de entrada (etiqueta -> valor)
        'resultados': {...},      # resultados del cálculo (etiqueta -> valor)
        'formula_texto': str,     # fórmula aplicada, para el papel de trabajo
        'semilla': int | None,    # semilla usada en la selección (evidencia NIA 530)
        'seleccion': [ {'numero': int, 'elemento': str}, ... ],
    }

Los errores de validación se lanzan como ValueError con mensaje en español.
"""

import math
import random
import zlib

# Valores Z por nivel de confianza (distribución normal estándar)
Z_TABLA = {80: 1.282, 90: 1.645, 95: 1.96, 99: 2.576}

# Factores de confiabilidad R para muestreo por unidad monetaria (MUS)
R_MUS = {80: 1.6, 90: 2.3, 95: 3.0, 99: 4.6}

NIVELES_VALIDOS = sorted(Z_TABLA.keys())


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _validar_confianza(nivel_confianza):
    """Valida el nivel de confianza y devuelve su valor entero."""
    try:
        nivel = int(nivel_confianza)
    except (TypeError, ValueError):
        raise ValueError("El nivel de confianza debe ser un número entero (80, 90, 95 o 99).")
    if nivel not in Z_TABLA:
        raise ValueError(
            f"Nivel de confianza no soportado: {nivel}. Valores permitidos: {NIVELES_VALIDOS}."
        )
    return nivel


def _validar_positivo(valor, nombre, estricto=True):
    """Valida que un parámetro numérico sea positivo (o no negativo si estricto=False)."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El parámetro '{nombre}' debe ser numérico.")
    if estricto and numero <= 0:
        raise ValueError(f"El parámetro '{nombre}' debe ser mayor que cero.")
    if not estricto and numero < 0:
        raise ValueError(f"El parámetro '{nombre}' no puede ser negativo.")
    return numero


def _validar_entero_positivo(valor, nombre):
    """Valida que un parámetro sea un entero mayor o igual a 1."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El parámetro '{nombre}' debe ser un número entero.")
    if numero < 1:
        raise ValueError(f"El parámetro '{nombre}' debe ser al menos 1.")
    return numero


def _derivar_semilla(semilla, audit_id, metodo, poblacion, n):
    """
    Devuelve la semilla a usar en la selección aleatoria.

    Si el auditor no indica una semilla, se deriva de forma determinista de
    (audit_id, método, población, n) para que la muestra sea reproducible
    como evidencia de auditoría (NIA 530).
    """
    if semilla not in (None, ''):
        try:
            return int(semilla)
        except (TypeError, ValueError):
            raise ValueError("La semilla debe ser un número entero.")
    base = f"{audit_id or 0}|{metodo}|{poblacion}|{n}"
    return zlib.crc32(base.encode('utf-8'))


def _correccion_poblacion_finita(n_calculado, poblacion):
    """Aplica la corrección por población finita cuando n excede N."""
    if n_calculado > poblacion:
        return n_calculado / (1 + ((n_calculado - 1) / poblacion)), True
    return n_calculado, False


def _seleccionar_indices(rng, poblacion, n, prefijo="Partida"):
    """
    Selecciona n índices sin reemplazo de 1..N y los devuelve ordenados.

    Además del rótulo, cada elemento lleva su 'indice' dentro de la población:
    es lo que permite localizar la partida real cuando la muestra se generó
    desde el Excel de datos importado.
    """
    indices = sorted(rng.sample(range(1, poblacion + 1), n))
    return [
        {'numero': posicion, 'elemento': f"{prefijo} {indice}", 'indice': indice}
        for posicion, indice in enumerate(indices, start=1)
    ]


def _formato_q(valor):
    """Formatea un monto con separador de miles, estilo Q 1,234,567.89."""
    return f"Q {valor:,.2f}"


# ---------------------------------------------------------------------------
# 1. Aleatorio Simple
# ---------------------------------------------------------------------------

def calcular_aleatorio_simple(nivel_confianza, tolerancia, poblacion, materialidad,
                              sigma, semilla=None, audit_id=None):
    """
    Muestreo aleatorio simple (NIA 530).

    e = materialidad * tolerancia
    n = (Z * sigma / e)^2, con corrección por población finita si n > N.
    """
    nivel = _validar_confianza(nivel_confianza)
    tolerancia = _validar_positivo(tolerancia, 'tolerancia')
    if tolerancia >= 1:
        raise ValueError("La tolerancia debe expresarse como fracción (por ejemplo 0.10 para 10%).")
    poblacion = _validar_entero_positivo(poblacion, 'población (N)')
    materialidad = _validar_positivo(materialidad, 'materialidad de ejecución')
    sigma = _validar_positivo(sigma, 'desviación estándar (sigma)')

    z = Z_TABLA[nivel]
    error_tolerable = materialidad * tolerancia
    n_calculado = (z * sigma / error_tolerable) ** 2
    n_corregido, fpc_aplicada = _correccion_poblacion_finita(n_calculado, poblacion)
    n = min(math.ceil(n_corregido), poblacion)
    cobertura = n / poblacion * 100

    semilla_usada = _derivar_semilla(semilla, audit_id, 'aleatorio_simple', poblacion, n)
    rng = random.Random(semilla_usada)
    seleccion = _seleccionar_indices(rng, poblacion, n)

    formula = (
        f"n = (Z × σ / e)² · Z({nivel}%) = {z} · σ = {_formato_q(sigma)} · "
        f"e = materialidad × tolerancia = {_formato_q(error_tolerable)}"
        + (" · corrección por población finita aplicada" if fpc_aplicada else "")
    )

    return {
        'metodo': 'aleatorio_simple',
        'metodo_nombre': 'Aleatorio Simple',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Nivel de confianza': f"{nivel}%",
            'Valor Z': z,
            'Tolerancia (% de materialidad)': f"{tolerancia * 100:.1f}%",
            'Población total (N)': poblacion,
            'Materialidad de ejecución (Q)': _formato_q(materialidad),
            'Desviación estándar σ (Q)': _formato_q(sigma),
        },
        'resultados': {
            'Tamaño de muestra (n)': n,
            'Cobertura de la población': f"{cobertura:.1f}%",
            'Error tolerable (e)': _formato_q(error_tolerable),
            'Corrección por población finita': 'Sí' if fpc_aplicada else 'No',
        },
        'formula_texto': formula,
        'semilla': semilla_usada,
        'seleccion': seleccion,
    }


# ---------------------------------------------------------------------------
# 2. Estratificado
# ---------------------------------------------------------------------------

def calcular_estratificado(nivel_confianza, tolerancia, materialidad, sigma,
                           n1, n2, n3, semilla=None, audit_id=None):
    """
    Muestreo estratificado (NIA 530, párr. A13).

    N = n1 + n2 + n3; n total con la misma fórmula del aleatorio simple (+FPC);
    asignación proporcional a cada estrato.
    """
    nivel = _validar_confianza(nivel_confianza)
    tolerancia = _validar_positivo(tolerancia, 'tolerancia')
    if tolerancia >= 1:
        raise ValueError("La tolerancia debe expresarse como fracción (por ejemplo 0.10 para 10%).")
    materialidad = _validar_positivo(materialidad, 'materialidad de ejecución')
    sigma = _validar_positivo(sigma, 'desviación estándar (sigma)')
    n1 = _validar_entero_positivo(n1, 'estrato 1 (alto valor)')
    n2 = _validar_entero_positivo(n2, 'estrato 2 (valor medio)')
    n3 = _validar_entero_positivo(n3, 'estrato 3 (bajo valor)')

    poblacion = n1 + n2 + n3
    z = Z_TABLA[nivel]
    error_tolerable = materialidad * tolerancia
    n_calculado = (z * sigma / error_tolerable) ** 2
    n_corregido, fpc_aplicada = _correccion_poblacion_finita(n_calculado, poblacion)
    n = min(math.ceil(n_corregido), poblacion)

    # Asignación proporcional al tamaño de cada estrato
    a1 = round(n * n1 / poblacion)
    a2 = round(n * n2 / poblacion)
    a3 = n - a1 - a2
    # Ajuste de bordes: ninguna asignación puede ser negativa ni exceder su estrato
    if a3 < 0:
        a2 += a3
        a3 = 0
    if a3 > n3:
        a2 += a3 - n3
        a3 = n3
    if a2 > n2:
        a1 += a2 - n2
        a2 = n2
    a1 = min(a1, n1)

    cobertura = n / poblacion * 100
    semilla_usada = _derivar_semilla(semilla, audit_id, 'estratificado', poblacion, n)
    rng = random.Random(semilla_usada)

    # Selección por estrato: los índices 1..n1 son alto valor, n1+1..n1+n2 valor
    # medio y el resto bajo valor (numeración continua sobre la población total)
    seleccion = []
    estratos_def = [
        ('Estrato 1 · Alto valor', 1, n1, a1),
        ('Estrato 2 · Valor medio', n1 + 1, n1 + n2, a2),
        ('Estrato 3 · Bajo valor', n1 + n2 + 1, poblacion, a3),
    ]
    posicion = 1
    for etiqueta, inicio, fin, asignados in estratos_def:
        if asignados <= 0:
            continue
        for indice in sorted(rng.sample(range(inicio, fin + 1), asignados)):
            seleccion.append({
                'numero': posicion,
                'elemento': f"Partida {indice} · {etiqueta}",
                'indice': indice,
            })
            posicion += 1

    formula = (
        f"n = (Z × σ / e)² con asignación proporcional por estrato · Z({nivel}%) = {z} · "
        f"σ = {_formato_q(sigma)} · e = {_formato_q(error_tolerable)}"
        + (" · corrección por población finita aplicada" if fpc_aplicada else "")
    )

    return {
        'metodo': 'estratificado',
        'metodo_nombre': 'Estratificado',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Nivel de confianza': f"{nivel}%",
            'Valor Z': z,
            'Tolerancia (% de materialidad)': f"{tolerancia * 100:.1f}%",
            'Materialidad de ejecución (Q)': _formato_q(materialidad),
            'Desviación estándar σ (Q)': _formato_q(sigma),
            'Estrato 1 · Alto valor (N)': n1,
            'Estrato 2 · Valor medio (N)': n2,
            'Estrato 3 · Bajo valor (N)': n3,
            'Población total (N)': poblacion,
        },
        'resultados': {
            'Muestra total (n)': n,
            'Cobertura de la población': f"{cobertura:.1f}%",
            'Muestra Estrato 1 (alto valor)': a1,
            'Muestra Estrato 2 (valor medio)': a2,
            'Muestra Estrato 3 (bajo valor)': a3,
            'Corrección por población finita': 'Sí' if fpc_aplicada else 'No',
        },
        'formula_texto': formula,
        'semilla': semilla_usada,
        'seleccion': seleccion,
    }


# ---------------------------------------------------------------------------
# 3. Monetario (MUS)
# ---------------------------------------------------------------------------

def calcular_mus(nivel_confianza, valor_libros, error_tolerable, error_esperado,
                 semilla=None, audit_id=None, partidas=None):
    """
    Muestreo por unidad monetaria — MUS (NIA 530, Apéndice 4).

    n = ceil(BV × R / (TE − EA)); intervalo = BV / n.

    Cuando se conoce el detalle de partidas (mayor auxiliar importado), la
    selección se hace como manda la práctica de MUS y NO se repite ninguna
    partida:

      · Las partidas cuyo monto es MAYOR O IGUAL al intervalo son
        individualmente significativas: entran al 100 %, una sola vez. Antes
        estas partidas absorbían varios puntos de selección y aparecían
        duplicadas en el papel de trabajo.
      · El resto se recorre con selección sistemática monetaria (arranque
        aleatorio + k × intervalo). Como todas esas partidas miden menos que el
        intervalo, cada punto cae en una partida distinta.

    Sin detalle de partidas (modo manual) se devuelven los puntos monetarios.
    """
    nivel = _validar_confianza(nivel_confianza)
    valor_libros = _validar_positivo(valor_libros, 'valor en libros (BV)')
    error_tolerable = _validar_positivo(error_tolerable, 'error tolerable (TE)')
    error_esperado = _validar_positivo(error_esperado, 'error esperado (EA)', estricto=False)
    if error_tolerable <= error_esperado:
        raise ValueError(
            "El error tolerable (TE) debe ser mayor que el error esperado (EA). "
            "Con estos valores la muestra no es determinable."
        )

    factor_r = R_MUS[nivel]
    n = math.ceil(valor_libros * factor_r / (error_tolerable - error_esperado))
    intervalo_exacto = valor_libros / n
    intervalo = round(intervalo_exacto)

    semilla_usada = _derivar_semilla(semilla, audit_id, 'mus', int(valor_libros), n)
    rng = random.Random(semilla_usada)
    arranque = rng.uniform(0, intervalo_exacto)

    resultados = {
        'Tamaño de muestra (n)': n,
        'Intervalo de muestreo (Q)': _formato_q(intervalo),
        'Arranque aleatorio (Q)': _formato_q(round(arranque, 2)),
    }

    if partidas:
        seleccion, extra = _seleccionar_mus_sobre_partidas(
            partidas, intervalo_exacto, arranque)
        resultados.update(extra)
    else:
        # Modo manual: solo puntos monetarios, sin partidas que mapear
        seleccion = []
        for k in range(n):
            punto = round(arranque + k * intervalo_exacto, 2)
            seleccion.append({
                'numero': k + 1,
                'elemento': f"Unidad monetaria {_formato_q(punto)}",
                'punto': punto,
            })

    formula = (
        "Memoria de cálculo (NIA 530, Apéndice 4):  "
        f"1) Factor de confiabilidad R({nivel}%) = {factor_r}.  "
        f"2) n = (BV × R) / (TE − EA) = ({_formato_q(valor_libros)} × {factor_r}) / "
        f"({_formato_q(error_tolerable)} − {_formato_q(error_esperado)}) = {n}.  "
        f"3) Intervalo de muestreo = BV / n = {_formato_q(valor_libros)} / {n} = "
        f"{_formato_q(intervalo)}.  "
        f"4) Arranque aleatorio dentro del primer intervalo = "
        f"{_formato_q(round(arranque, 2))} (semilla {semilla_usada}, reproducible).  "
        "5) Las partidas con monto ≥ intervalo se examinan al 100 % por ser "
        "individualmente significativas; el resto se selecciona de forma "
        "sistemática (arranque + k × intervalo), sin repetir partidas."
    )

    return {
        'metodo': 'mus',
        'metodo_nombre': 'Monetario (MUS)',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Nivel de confianza': f"{nivel}%",
            'Factor de confiabilidad (R)': factor_r,
            'Libro Mayor Total / BV (Q)': _formato_q(valor_libros),
            'Error tolerable / TE (Q)': _formato_q(error_tolerable),
            'Error esperado / EA (Q)': _formato_q(error_esperado),
        },
        'resultados': resultados,
        'formula_texto': formula,
        'semilla': semilla_usada,
        'seleccion': seleccion,
    }


def _seleccionar_mus_sobre_partidas(partidas, intervalo, arranque):
    """
    Selección MUS real sobre el detalle del mayor auxiliar, sin duplicados.

    Devuelve (seleccion, resultados_extra). Cada elemento de *seleccion* lleva
    el índice (1-based) de su partida en el archivo y la marca que explica por
    qué fue seleccionada.
    """
    for partida in partidas:
        if partida.get('monto', 0) < 0:
            raise ValueError(
                "El muestreo monetario (MUS) requiere montos no negativos: la partida "
                f"{partida.get('no')} ({partida.get('documento')}) tiene monto negativo. "
                "Depure el mayor auxiliar o use otro método."
            )

    # 1) Partidas individualmente significativas (monto >= intervalo): 100 %
    significativas = []
    resto = []
    for indice, partida in enumerate(partidas, start=1):
        if partida['monto'] >= intervalo:
            significativas.append((indice, partida))
        else:
            resto.append((indice, partida))

    seleccion = []
    for indice, partida in significativas:
        seleccion.append({
            'numero': len(seleccion) + 1,
            'elemento': f"{partida['documento']} · {_formato_q(partida['monto'])}",
            'indice': indice,
            'marca': '100 % (individualmente significativa)',
        })

    # 2) Selección sistemática monetaria sobre el resto
    acumulado = 0.0
    tramos = []
    for indice, partida in resto:
        acumulado += partida['monto']
        tramos.append((acumulado, indice, partida))

    total_resto = acumulado
    if total_resto > 0:
        posicion = 0
        punto = arranque
        while punto <= total_resto:
            while posicion < len(tramos) and tramos[posicion][0] < punto:
                posicion += 1
            if posicion >= len(tramos):
                break
            _, indice, partida = tramos[posicion]
            seleccion.append({
                'numero': len(seleccion) + 1,
                'elemento': f"{partida['documento']} · {_formato_q(partida['monto'])}",
                'indice': indice,
                'marca': 'Selección sistemática',
                'punto': round(punto, 2),
            })
            posicion += 1  # cada partida se toma una sola vez
            punto += intervalo

    monto_seleccionado = math.fsum(
        partidas[item['indice'] - 1]['monto'] for item in seleccion)
    monto_total = math.fsum(partida['monto'] for partida in partidas)

    extra = {
        'Partidas al 100 % (≥ intervalo)': len(significativas),
        'Partidas por selección sistemática': len(seleccion) - len(significativas),
        'Total de partidas distintas seleccionadas': len(seleccion),
        'Cobertura monetaria de la muestra': (
            f"{monto_seleccionado / monto_total * 100:.1f}%" if monto_total else '0.0%'
        ),
    }
    return seleccion, extra


# ---------------------------------------------------------------------------
# 4. Por Atributos
# ---------------------------------------------------------------------------

def calcular_atributos(nivel_confianza, desviacion_tolerable, tasa_esperada,
                       poblacion, semilla=None, audit_id=None):
    """
    Muestreo por atributos para pruebas de controles (NIA 330 / NIA 530).

    n = ceil(Z² × p(1−p) / d²), limitado a N.
    """
    nivel = _validar_confianza(nivel_confianza)
    desviacion_tolerable = _validar_positivo(desviacion_tolerable, 'desviación tolerable (d)')
    if desviacion_tolerable >= 1:
        raise ValueError("La desviación tolerable debe expresarse como fracción (por ejemplo 0.10 para 10%).")
    tasa_esperada = _validar_positivo(tasa_esperada, 'tasa esperada de desviación (p)', estricto=False)
    if tasa_esperada >= 1:
        raise ValueError("La tasa esperada de desviación debe expresarse como fracción (por ejemplo 0.025 para 2.5%).")
    poblacion = _validar_entero_positivo(poblacion, 'población (N)')

    z = Z_TABLA[nivel]
    n = math.ceil((z ** 2) * tasa_esperada * (1 - tasa_esperada) / (desviacion_tolerable ** 2))
    n = min(n, poblacion)
    cobertura = n / poblacion * 100

    semilla_usada = _derivar_semilla(semilla, audit_id, 'atributos', poblacion, n)
    rng = random.Random(semilla_usada)
    seleccion = _seleccionar_indices(rng, poblacion, n, prefijo="Control ejecutado")

    formula = (
        f"n = (Z² × p(1−p)) / d² · Z({nivel}%) = {z} · p = {tasa_esperada * 100:.1f}% · "
        f"d = {desviacion_tolerable * 100:.0f}%. Si se detectan desviaciones al ejecutar la prueba, "
        f"documente la tasa observada y compárela contra d (NIA 330)."
    )

    return {
        'metodo': 'atributos',
        'metodo_nombre': 'Por Atributos',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Nivel de confianza': f"{nivel}%",
            'Valor Z': z,
            'Desviación tolerable (d)': f"{desviacion_tolerable * 100:.0f}%",
            'Tasa esperada de desviación (p)': f"{tasa_esperada * 100:.1f}%",
            'Población (N° de controles ejecutados)': poblacion,
        },
        'resultados': {
            'Tamaño de muestra (n)': n,
            'Cobertura de la población': f"{cobertura:.1f}%",
            'Desviación tolerable': f"{desviacion_tolerable * 100:.0f}%",
        },
        'formula_texto': formula,
        'semilla': semilla_usada,
        'seleccion': seleccion,
    }


# ---------------------------------------------------------------------------
# 5. Por Criterio (selección dirigida)
# ---------------------------------------------------------------------------

def calcular_criterio(partidas=None, valor_total=None, porcentaje_examinar=30,
                      monto_mayor=None, monto_menor=0, audit_id=None):
    """
    Selección dirigida por criterio de monto (NIA 530, párr. 5).

    Trabaja sobre el detalle transaccional (mayor auxiliar importado o pegado) y
    aplica los criterios que definió el cliente:

      1. Toda partida con monto ≥ 'Monto mayor a' se selecciona al 100 %
         (partida individualmente significativa).
      2. Si con esas no se cubre el '% del total a examinar', se completa con
         las partidas de mayor monto que queden, siempre por encima de
         'Monto menor a' (las de abajo se consideran triviales y se excluyen).

    No es muestreo estadístico: los resultados no se proyectan a la población.
    """
    if not isinstance(partidas, list) or len(partidas) == 0:
        raise ValueError(
            "Suba el Excel del detalle transaccional (N.º Documento · Descripción · "
            "Fecha · Monto) o pegue las partidas para poder aplicar los criterios."
        )

    normalizadas = []
    for posicion, partida in enumerate(partidas, start=1):
        if not isinstance(partida, dict):
            raise ValueError(f"La partida {posicion} tiene un formato inválido.")
        monto = _validar_positivo(
            partida.get('monto'), f"monto de la partida {posicion}", estricto=False)
        normalizadas.append({
            'indice': posicion,
            'documento': str(partida.get('documento', '') or '').strip(),
            'descripcion': str(partida.get('descripcion', '') or '').strip(),
            'fecha': str(partida.get('fecha', '') or '').strip(),
            'monto': monto,
        })

    porcentaje = _validar_positivo(porcentaje_examinar, '% del total a examinar')
    if porcentaje > 100:
        raise ValueError("El '% del total a examinar' no puede ser mayor que 100.")
    monto_menor = _validar_positivo(monto_menor, "'Monto menor a'", estricto=False)

    suma_detalle = math.fsum(item['monto'] for item in normalizadas)
    if valor_total in (None, '', 0):
        total = suma_detalle
    else:
        total = _validar_positivo(valor_total, 'Valor Monetario Total')
    if total <= 0:
        raise ValueError(
            "El Valor Monetario Total es cero: revise los montos del detalle cargado.")

    if monto_mayor in (None, ''):
        raise ValueError("Indique el 'Monto mayor a (Q)' para la selección al 100 %.")
    monto_mayor = _validar_positivo(monto_mayor, "'Monto mayor a'")
    if monto_menor >= monto_mayor:
        raise ValueError(
            "El 'Monto menor a' debe ser inferior al 'Monto mayor a': con estos valores "
            "no queda ninguna partida para la muestra complementaria."
        )

    objetivo = total * porcentaje / 100

    # 1) Partidas individualmente significativas
    significativas = [item for item in normalizadas if item['monto'] >= monto_mayor]
    acumulado = math.fsum(item['monto'] for item in significativas)

    # 2) Complementarias: de mayor a menor, sin bajar del umbral de trivialidad
    candidatas = sorted(
        (item for item in normalizadas
         if monto_menor <= item['monto'] < monto_mayor),
        key=lambda item: item['monto'], reverse=True,
    )
    complementarias = []
    for item in candidatas:
        if acumulado >= objetivo:
            break
        complementarias.append(item)
        acumulado += item['monto']

    seleccion = []
    for item in significativas:
        seleccion.append({
            'numero': len(seleccion) + 1,
            'elemento': (f"{item['documento']} · {item['descripcion']} · "
                         f"{_formato_q(item['monto'])}"),
            'indice': item['indice'],
            'marca': '100 % (individualmente significativa)',
        })
    for item in complementarias:
        seleccion.append({
            'numero': len(seleccion) + 1,
            'elemento': (f"{item['documento']} · {item['descripcion']} · "
                         f"{_formato_q(item['monto'])}"),
            'indice': item['indice'],
            'marca': 'Complementaria',
        })

    if not seleccion:
        raise ValueError(
            "Ninguna partida cumple los criterios indicados: baje el 'Monto mayor a' "
            "o el 'Monto menor a' para que la selección alcance el porcentaje pedido."
        )

    triviales = [item for item in normalizadas if item['monto'] < monto_menor]

    return {
        'metodo': 'criterio',
        'metodo_nombre': 'Por Criterio',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Tipo de selección': 'Dirigida (no estadística)',
            'Partidas en el detalle': len(normalizadas),
            'Valor Monetario Total (Q)': _formato_q(total),
            '% del total a examinar': f"{porcentaje:.0f}%",
            'Monto mayor a (Q) — al 100 %': _formato_q(monto_mayor),
            'Monto menor a (Q) — se excluye': _formato_q(monto_menor),
        },
        'resultados': {
            'Valor objetivo a examinar (Q)': _formato_q(objetivo),
            'Partidas seleccionadas': len(seleccion),
            'Partidas al 100 % (≥ monto mayor)': len(significativas),
            'Partidas complementarias': len(complementarias),
            'Monto total seleccionado (Q)': _formato_q(acumulado),
            'Cobertura del valor total': f"{acumulado / total * 100:.1f}%",
            'Partidas triviales excluidas (< monto menor)': len(triviales),
        },
        'formula_texto': (
            f"Selección dirigida por criterio de monto (NIA 530, párr. 5). "
            f"Valor objetivo = Valor Monetario Total × % a examinar = "
            f"{_formato_q(total)} × {porcentaje:.0f}% = {_formato_q(objetivo)}. "
            f"Se seleccionan al 100 % las {len(significativas)} partidas con monto ≥ "
            f"{_formato_q(monto_mayor)} y se completan {len(complementarias)} partidas "
            f"complementarias de mayor a menor hasta cubrir el objetivo, excluyendo las "
            f"{len(triviales)} partidas triviales por debajo de {_formato_q(monto_menor)}. "
            f"Cobertura alcanzada: {_formato_q(acumulado)} "
            f"({acumulado / total * 100:.1f}% del valor total). "
            "No es muestreo estadístico: los resultados no se proyectan a la población."
        ),
        'semilla': None,
        'seleccion': seleccion,
    }


# ---------------------------------------------------------------------------
# Despachador por método
# ---------------------------------------------------------------------------

def calcular_muestreo(metodo, datos, audit_id=None, partidas=None):
    """
    Punto de entrada único: recibe la clave del método y el diccionario de
    parámetros (por ejemplo el cuerpo JSON de la vista) y despacha al cálculo
    correspondiente.

    *partidas* es el detalle del mayor auxiliar cuando el auditor generó la
    muestra desde el Excel de datos. MUS y Por Criterio lo necesitan para
    seleccionar partidas reales; el resto de métodos trabaja por índice.
    """
    semilla = datos.get('semilla')
    if partidas is None:
        partidas = datos.get('partidas')
    if metodo == 'aleatorio_simple':
        return calcular_aleatorio_simple(
            datos.get('nivel_confianza'), datos.get('tolerancia'), datos.get('poblacion'),
            datos.get('materialidad'), datos.get('sigma'),
            semilla=semilla, audit_id=audit_id,
        )
    if metodo == 'estratificado':
        return calcular_estratificado(
            datos.get('nivel_confianza'), datos.get('tolerancia'), datos.get('materialidad'),
            datos.get('sigma'), datos.get('n1'), datos.get('n2'), datos.get('n3'),
            semilla=semilla, audit_id=audit_id,
        )
    if metodo == 'mus':
        return calcular_mus(
            datos.get('nivel_confianza'), datos.get('valor_libros'),
            datos.get('error_tolerable'), datos.get('error_esperado'),
            semilla=semilla, audit_id=audit_id, partidas=partidas,
        )
    if metodo == 'atributos':
        return calcular_atributos(
            datos.get('nivel_confianza'), datos.get('desviacion_tolerable'),
            datos.get('tasa_esperada'), datos.get('poblacion'),
            semilla=semilla, audit_id=audit_id,
        )
    if metodo == 'criterio':
        return calcular_criterio(
            partidas=partidas,
            valor_total=datos.get('valor_total'),
            porcentaje_examinar=datos.get('porcentaje_examinar', 30),
            monto_mayor=datos.get('monto_mayor'),
            monto_menor=datos.get('monto_menor', 0),
            audit_id=audit_id,
        )
    raise ValueError(f"Método de muestreo desconocido: {metodo}")
