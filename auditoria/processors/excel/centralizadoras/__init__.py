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


def process_centralizadora_file(workbook, balances, ajustes_reclasificaciones, file_name):
    """
    Procesa archivos CENTRALIZADORA según su tipo

    Args:
        workbook: El libro de Excel a procesar
        balances: Diccionario con los balances financieros
        file_name: Nombre del archivo a procesar

    Returns:
        El libro de Excel procesado
    """
    # Obtener todas las fechas semestrales disponibles
    fechas_semestrales = obtener_todas_fechas_semestrales(balances)
    if not fechas_semestrales:
        return workbook

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

    # Identificar el tipo de archivo
    tipo_archivo = None
    for tipo in tipos_archivo:
        if tipo in file_name:
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

    # Procesar el archivo con la función correspondiente
    funcion_procesamiento(
        workbook,
        cuentas_por_fecha,
        fechas_semestrales,
        ajustes_reclasificaciones,
    )

    return workbook
