from ..fechas import resolver_fechas_columnas, insertar_fechas_en_celdas
from ..inserter import procesar_seccion_centralizadora
from ..utils import buscar_fila_por_valor

def insertar_datos_activo(workbook, cuentas_por_fecha, fechas_semestrales,
                          ajustes_reclasificaciones, cortes=None):
    sheet = workbook.active

    fechas_columnas, fechas_excel = resolver_fechas_columnas(fechas_semestrales, cortes)
    insertar_fechas_en_celdas(sheet, fechas_excel)

    procesar_seccion_centralizadora(
        sheet=sheet,
        cuentas_por_fecha=cuentas_por_fecha,
        fechas_columnas=fechas_columnas,
        ajustes_reclasificaciones=ajustes_reclasificaciones,
        secciones=['Activo'],
        fila_inicio=13,
        texto_suma='Suma Activo',
        columnas_suma=['D', 'E', 'F', 'G', 'H', 'I']
    )
