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
                 semilla=None, audit_id=None):
    """
    Muestreo por unidad monetaria — MUS (NIA 530, Apéndice 4).

    n = ceil(BV × R / (TE − EA)); intervalo = round(BV / n).
    Selección sistemática: arranque aleatorio en [0, intervalo) y puntos
    monetarios arranque + k × intervalo.
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
    intervalo = round(valor_libros / n)

    semilla_usada = _derivar_semilla(semilla, audit_id, 'mus', int(valor_libros), n)
    rng = random.Random(semilla_usada)
    arranque = rng.uniform(0, intervalo)

    # Selección sistemática en unidades monetarias
    seleccion = []
    for k in range(n):
        punto = round(arranque + k * intervalo, 2)
        seleccion.append({
            'numero': k + 1,
            'elemento': f"Unidad monetaria {_formato_q(punto)}",
            'punto': punto,
        })

    formula = (
        f"n = (BV × R) / (TE − EA) · BV = {_formato_q(valor_libros)} · R({nivel}%) = {factor_r} · "
        f"TE = {_formato_q(error_tolerable)} · EA = {_formato_q(error_esperado)} · "
        f"selección sistemática con arranque aleatorio {_formato_q(round(arranque, 2))}"
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
        'resultados': {
            'Tamaño de muestra (n)': n,
            'Intervalo de muestreo (Q)': _formato_q(intervalo),
            'Arranque aleatorio (Q)': _formato_q(round(arranque, 2)),
        },
        'formula_texto': formula,
        'semilla': semilla_usada,
        'seleccion': seleccion,
    }


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

def calcular_criterio(partidas, audit_id=None):
    """
    Selección dirigida por criterio del auditor (NIA 530, párr. 5).

    No es muestreo estadístico: el auditor lista manualmente las partidas
    seleccionadas (descripción, monto, criterio) y estas se documentan tal cual
    en el papel de trabajo. Los resultados no se proyectan a la población.
    """
    if not isinstance(partidas, list) or len(partidas) == 0:
        raise ValueError("Debe registrar al menos una partida seleccionada por criterio.")

    seleccion = []
    monto_total = 0.0
    for posicion, partida in enumerate(partidas, start=1):
        if not isinstance(partida, dict):
            raise ValueError(f"La partida {posicion} tiene un formato inválido.")
        descripcion = str(partida.get('descripcion', '')).strip()
        criterio = str(partida.get('criterio', '')).strip()
        if not descripcion:
            raise ValueError(f"La partida {posicion} no tiene descripción.")
        if not criterio:
            raise ValueError(f"La partida {posicion} no tiene criterio de selección.")
        monto = _validar_positivo(partida.get('monto'), f"monto de la partida {posicion}", estricto=False)
        monto_total += monto
        seleccion.append({
            'numero': posicion,
            'elemento': f"{descripcion} · {_formato_q(monto)} · Criterio: {criterio}",
        })

    return {
        'metodo': 'criterio',
        'metodo_nombre': 'Por Criterio',
        'nia_ref': 'NIA 530',
        'parametros': {
            'Tipo de selección': 'Dirigida (no estadística)',
            'Partidas registradas': len(seleccion),
        },
        'resultados': {
            'Partidas seleccionadas': len(seleccion),
            'Monto total seleccionado (Q)': _formato_q(monto_total),
        },
        'formula_texto': (
            "Selección dirigida según el criterio profesional del auditor (NIA 530, párr. 5). "
            "No es muestreo estadístico: los resultados no se proyectan a la población."
        ),
        'semilla': None,
        'seleccion': seleccion,
    }


# ---------------------------------------------------------------------------
# Despachador por método
# ---------------------------------------------------------------------------

def calcular_muestreo(metodo, datos, audit_id=None):
    """
    Punto de entrada único: recibe la clave del método y el diccionario de
    parámetros (por ejemplo el cuerpo JSON de la vista) y despacha al cálculo
    correspondiente.
    """
    semilla = datos.get('semilla')
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
            semilla=semilla, audit_id=audit_id,
        )
    if metodo == 'atributos':
        return calcular_atributos(
            datos.get('nivel_confianza'), datos.get('desviacion_tolerable'),
            datos.get('tasa_esperada'), datos.get('poblacion'),
            semilla=semilla, audit_id=audit_id,
        )
    if metodo == 'criterio':
        return calcular_criterio(datos.get('partidas'), audit_id=audit_id)
    raise ValueError(f"Método de muestreo desconocido: {metodo}")
