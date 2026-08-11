"""
Cortes y totales del Excel Financiero guardados por auditoría.

El Excel Financiero 2026 trae cuatro columnas de saldos en la hoja
'ESTADOS FINANCIEROS':

    C = primer corte  ·  D = segundo corte  ·  E = tercer corte (cierre)
    H = corte del año actual (saldo ajustado)

En la base solo se conservan pares (fecha, valor), así que si el archivo se
rotula con fechas atípicas (o repite la misma fecha en E y H, como el archivo
del cliente, que solo audita UN año) los escritores no podrían saber a qué
columna pertenece cada corte. Para eso el importador guarda aquí las fechas
tal cual venían y los escritores de centralizadoras/sumarias rotulan sus
columnas con las fechas REALES del archivo.

También se capturan los totales 'Total Ingresos' / 'Utilidad antes de
impuesto' que el archivo trae como filas de total (no como cuentas), para que
Materialidad e Importancia Relativa muestren cifras trazables al archivo.
"""

from auditoria.models import ParametrosAuditoria

__all__ = [
    'guardar_cortes_desde_import',
    'guardar_totales_er_desde_import',
    'cortes_de_auditoria',
    'totales_er_de_auditoria',
]


def guardar_cortes_desde_import(audit_id, fecha1, fecha2, fecha3, fecha_actual):
    """Guarda las fechas de corte (columnas C/D/E/H) del archivo importado."""
    parametros, _ = ParametrosAuditoria.objects.get_or_create(audit_id=audit_id)
    parametros.fecha_corte1_excel = fecha1
    parametros.fecha_corte2_excel = fecha2
    parametros.fecha_corte3_excel = fecha3
    parametros.fecha_corte_actual_excel = fecha_actual
    parametros.save(update_fields=[
        'fecha_corte1_excel', 'fecha_corte2_excel', 'fecha_corte3_excel',
        'fecha_corte_actual_excel', 'actualizado_en',
    ])
    return parametros


def guardar_totales_er_desde_import(audit_id, ingresos_totales, utilidad_antes_impuestos):
    """Guarda los totales del Estado de Resultados capturados del archivo."""
    parametros, _ = ParametrosAuditoria.objects.get_or_create(audit_id=audit_id)
    parametros.ingresos_totales_excel = ingresos_totales
    parametros.utilidad_antes_impuestos_excel = utilidad_antes_impuestos
    parametros.save(update_fields=[
        'ingresos_totales_excel', 'utilidad_antes_impuestos_excel',
        'actualizado_en',
    ])
    return parametros


def cortes_de_auditoria(audit_id):
    """
    Devuelve los cortes del último Excel importado como dict:

        {'cortes': [fecha1, fecha2, fecha3], 'actual': fecha_actual}

    con `date` o None en cada posición, o None si la auditoría no tiene
    cortes guardados (importaciones con el formato clásico).
    """
    if not audit_id:
        return None
    parametros = ParametrosAuditoria.objects.filter(audit_id=audit_id).first()
    if not parametros:
        return None

    cortes = [
        parametros.fecha_corte1_excel,
        parametros.fecha_corte2_excel,
        parametros.fecha_corte3_excel,
    ]
    actual = parametros.fecha_corte_actual_excel

    if not any(cortes) and not actual:
        return None
    return {'cortes': cortes, 'actual': actual}


def totales_er_de_auditoria(audit_id):
    """(ingresos_totales, utilidad_antes_impuestos) capturados o (None, None)."""
    if not audit_id:
        return None, None
    parametros = ParametrosAuditoria.objects.filter(audit_id=audit_id).first()
    if not parametros:
        return None, None
    return (
        parametros.ingresos_totales_excel,
        parametros.utilidad_antes_impuestos_excel,
    )
