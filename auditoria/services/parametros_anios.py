"""
Años de la auditoría (actual / anterior) usados por los cuadros comparativos.

Regla acordada con el cliente (observación 1 del documento de respuestas):

  · Al importar el Excel Financiero, los años se toman AUTOMÁTICAMENTE de las
    fechas de corte del archivo (columna E = cierre anterior, columna H =
    cierre actual) y se guardan en `ParametrosAuditoria`.
  · El auditor puede editarlos a mano desde la pantalla de Papeles de Trabajo.
    Cuando lo hace, su valor manda y una reimportación NO se lo pisa salvo que
    el Excel traiga años distintos a los que originaron el dato automático.
  · Los cuadros comparativos (Análisis Horizontal/Vertical, Importancia
    Relativa, Materialidad) rotulan sus columnas con estos años.

Si el Excel trae la MISMA fecha (o el mismo año) en los dos cortes, la
auditoría es de UN solo ejercicio («si es 2025 pues es 2025»): el año
anterior queda VACÍO, los cuadros comparativos rotulan únicamente el año
actual y no se muestra ninguna columna de un año que el archivo no trae.
El auditor puede fijar un año anterior a mano si su trabajo sí compara dos
ejercicios.
"""

from auditoria.models import ParametrosAuditoria

__all__ = [
    'obtener_parametros',
    'anios_de_auditoria',
    'actualizar_anios_desde_import',
    'guardar_anios_manuales',
]


def obtener_parametros(audit_id):
    """Devuelve (creando si hace falta) la fila de parámetros de la auditoría."""
    parametros, _ = ParametrosAuditoria.objects.get_or_create(audit_id=audit_id)
    return parametros


def anios_de_auditoria(audit_id):
    """
    Devuelve (anio_actual, anio_anterior) como enteros o (None, None).

    Es la fuente única que consultan los escritores de plantillas para rotular
    las columnas de año.
    """
    parametros = ParametrosAuditoria.objects.filter(audit_id=audit_id).first()
    if not parametros:
        return None, None
    return parametros.anio_actual, parametros.anio_anterior


def _anio_de(fecha):
    return fecha.year if fecha else None


def actualizar_anios_desde_import(audit_id, fecha_cierre_anterior, fecha_cierre_actual):
    """
    Actualiza los años a partir de las fechas de corte del Excel importado.

    Args:
        audit_id: id de la auditoría
        fecha_cierre_anterior: fecha de la columna E ('Fecha corte año anterior')
        fecha_cierre_actual: fecha de la columna H ('Fecha corte año actual')

    Returns:
        (anio_actual, anio_anterior) ya persistidos.
    """
    anio_actual = _anio_de(fecha_cierre_actual)
    anio_anterior = _anio_de(fecha_cierre_anterior)

    # Cortes del mismo año -> el Excel solo trae UN ejercicio ('si es 2025
    # pues es 2025'): el año anterior queda vacío y los comparativos rotulan
    # únicamente el año actual. No se inventa un 'año actual - 1'.
    if anio_actual and anio_anterior == anio_actual:
        anio_anterior = None

    if anio_actual is None and anio_anterior is None:
        return anios_de_auditoria(audit_id)

    parametros = obtener_parametros(audit_id)

    # Los años que trae ESTE archivo se registran siempre, para poder comparar
    # en la siguiente importación.
    mismo_ejercicio_que_la_ultima_vez = (
        parametros.anio_actual_excel == anio_actual
        and parametros.anio_anterior_excel == anio_anterior
    )
    parametros.anio_actual_excel = anio_actual
    parametros.anio_anterior_excel = anio_anterior

    # Si el auditor fijó los años a mano, solo los reemplaza un archivo que
    # realmente cambió de ejercicio; reimportar el mismo Excel no se los pisa.
    if parametros.anios_manuales and mismo_ejercicio_que_la_ultima_vez:
        parametros.save(update_fields=[
            'anio_actual_excel', 'anio_anterior_excel', 'actualizado_en',
        ])
        return parametros.anio_actual, parametros.anio_anterior

    parametros.anio_actual = anio_actual
    parametros.anio_anterior = anio_anterior
    parametros.anios_manuales = False
    parametros.save(update_fields=[
        'anio_actual', 'anio_anterior', 'anios_manuales',
        'anio_actual_excel', 'anio_anterior_excel', 'actualizado_en',
    ])

    return anio_actual, anio_anterior


def guardar_anios_manuales(audit_id, anio_actual, anio_anterior):
    """
    Guarda los años editados por el auditor y los marca como manuales.

    Lanza ValueError con mensaje en español si los valores no son años válidos.
    """
    def _validar(valor, etiqueta):
        if valor in (None, ''):
            return None
        try:
            anio = int(valor)
        except (TypeError, ValueError):
            raise ValueError(f'El {etiqueta} debe ser un año de 4 dígitos.')
        if not 1900 <= anio <= 2200:
            raise ValueError(f'El {etiqueta} debe estar entre 1900 y 2200.')
        return anio

    anio_actual = _validar(anio_actual, 'año actual')
    anio_anterior = _validar(anio_anterior, 'año anterior')

    if anio_actual and anio_anterior and anio_anterior >= anio_actual:
        raise ValueError('El año anterior debe ser menor que el año actual.')

    parametros = obtener_parametros(audit_id)
    parametros.anio_actual = anio_actual
    parametros.anio_anterior = anio_anterior
    parametros.anios_manuales = True
    parametros.save(update_fields=['anio_actual', 'anio_anterior', 'anios_manuales', 'actualizado_en'])

    return anio_actual, anio_anterior
