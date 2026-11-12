from .fechas import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    obtener_todas_fechas_semestrales,
    filtrar_cuentas_por_seccion
)
from .tipos import (
    insertar_datos_activo,
    insertar_datos_balance,
    insertar_datos_pasivo_patrimonio,
    insertar_datos_estado_resultados
)


def process_centralizadora_file(workbook, balances, ajustes_reclasificaciones,
                                file_name, audit_id=None):
    """
    Procesa archivos CENTRALIZADORA según su tipo

    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros
        file_name: Nombre del archivo a procesar
        audit_id: id de la auditoría; permite rotular las columnas con las
            fechas de corte REALES del Excel importado (si están guardadas)

    Returns:
        El libro de Excel procesado
    """
    # Obtener todas las fechas semestrales disponibles
    fechas_semestrales = obtener_todas_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook

    # Cortes reales del último Excel Financiero importado (o None si la
    # auditoría se cargó con el formato clásico).
    try:
        from auditoria.services.cortes_excel import cortes_de_auditoria
        cortes = cortes_de_auditoria(audit_id)
    except Exception:
        cortes = None

    # Guarda: si los cortes guardados no corresponden a los balances actuales
    # (p. ej. luego se reimportó un archivo del formato clásico), se ignoran.
    if cortes:
        fechas_guardadas = {
            f.isoformat()
            for f in list(cortes.get('cortes') or []) + [cortes.get('actual')]
            if f
        }
        if not fechas_guardadas & set(fechas_semestrales):
            cortes = None

    # Mapeo de tipos de archivo a secciones y funciones de procesamiento
    tipos_archivo = {
        "BALANCE": {
            "secciones": ["Activo", "Pasivo", "Patrimonio"],
            "funcion": insertar_datos_balance
        },
        "ACTIVO": {
            "secciones": ["Activo"],
            "funcion": insertar_datos_activo
        },
        "PASIVO Y PATRIMONIO": {
            "secciones": ["Pasivo", "Patrimonio"],
            "funcion": insertar_datos_pasivo_patrimonio
        },
        "ESTADO DE RESULTADOS": {
            "secciones": ["ESTADO DE RESULTADOS"],
            "funcion": insertar_datos_estado_resultados
        }
    }

    # Identificar el tipo de archivo.
    # Las plantillas 2026 usan guiones bajos en el nombre (p. ej.
    # "CENTRALIZADORA_DEL_PASIVO_Y_PATRIMONIO.xlsx"), por lo que se normaliza
    # el nombre (guion bajo -> espacio, espacios colapsados) antes de comparar.
    import re as _re
    nombre_normalizado = _re.sub(r"\s+", " ", file_name.replace("_", " "))
    tipo_archivo = None
    for tipo in tipos_archivo:
        if tipo in nombre_normalizado:
            tipo_archivo = tipo
            break

    if not tipo_archivo:
        return workbook

    # Obtener las secciones y función de procesamiento para este tipo de archivo
    secciones = tipos_archivo[tipo_archivo]["secciones"]
    funcion_procesamiento = tipos_archivo[tipo_archivo]["funcion"]

    # Obtener las cuentas para cada sección
    cuentas_por_fecha = {}
    for fecha in fechas_semestrales:
        if tipo_archivo in ["BALANCE", "PASIVO Y PATRIMONIO"]:
            # Para BALANCE y PASIVO Y PATRIMONIO, necesitamos mantener la estructura con secciones
            cuentas_por_fecha[fecha] = {}
            for seccion in secciones:
                cuentas = filtrar_cuentas_por_seccion(balances, fecha, seccion)
                cuentas_por_fecha[fecha][seccion] = cuentas
        else:
            # Para los demás tipos, solo necesitamos las cuentas de una sección
            seccion = secciones[0]
            cuentas = filtrar_cuentas_por_seccion(balances, fecha, seccion)
            cuentas_por_fecha[fecha] = cuentas

    # Respetar el comportamiento productivo con ausencia de datos del rubro:
    # si existe balance de otra sección pero ninguna cuenta de esta
    # centralizadora, NO invocar el insertador con diccionarios vacíos
    # (la versión anterior lanzaba IndexError y devolvía HTTP 500).
    if not any(cuentas_por_fecha.values()):
        return workbook

    # Procesar el archivo con la función correspondiente
    funcion_procesamiento(
        workbook,
        cuentas_por_fecha,
        fechas_semestrales,
        ajustes_reclasificaciones,
        cortes=cortes,
    )

    return workbook
