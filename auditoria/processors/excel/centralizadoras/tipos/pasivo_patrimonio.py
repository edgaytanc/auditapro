from ..fechas import preparar_fechas_excel, insertar_fechas_en_celdas
from ..inserter import procesar_seccion_centralizadora
from ..utils import buscar_fila_por_valor

def insertar_datos_pasivo_patrimonio(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    sheet = workbook.active

    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    insertar_fechas_en_celdas(sheet, fechas_excel)

    fechas_columnas = {
        'D': fechas_año_viejo[0],
        'E': fechas_año_viejo[1],
        'F': fechas_año_viejo[2],
        'I': fecha_mas_reciente
    }

    procesar_seccion_centralizadora(
        sheet=sheet,
        cuentas_por_fecha=cuentas_por_fecha,
        fechas_columnas=fechas_columnas,
        ajustes_reclasificaciones=ajustes_reclasificaciones,
        secciones=['Pasivo', 'Patrimonio'],
        fila_inicio=13,
        texto_suma='Suma Pasivo y Patrimonio',
        columnas_suma=['D', 'E', 'F', 'G', 'H', 'I']
    )
