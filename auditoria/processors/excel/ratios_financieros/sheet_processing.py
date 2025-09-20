from .inserter import insertar_cuentas_en_rango
from .utils import encontrar_columnas_años, obtener_rangos_fijos_por_hoja
import logging

logger = logging.getLogger(__name__)

def procesar_hoja_comparativo(sheet, cuentas_clasificadas, año_actual, año_anterior):
    """Procesa la hoja 'Estados Financieros Comparativo'."""
    columnas = encontrar_columnas_años(sheet)
    if not columnas.get('año_actual') or not columnas.get('año_anterior'):
        logger.error(f"No se encontraron las columnas de años en la hoja {sheet.title}")
        return

    rangos = obtener_rangos_fijos_por_hoja(sheet.title)

    # Mapeo de secciones a procesar
    secciones_a_procesar = {
        'Activo Corriente': (rangos['activo_corriente'], cuentas_clasificadas['Activo']['Corriente']),
        'Activo No Corriente': (rangos['activo_no_corriente'], cuentas_clasificadas['Activo']['No Corriente']),
        'Pasivo Corriente': (rangos['pasivo_corriente'], cuentas_clasificadas['Pasivo']['Corriente']),
        'Pasivo No Corriente': (rangos['pasivo_no_corriente'], cuentas_clasificadas['Pasivo']['No Corriente']),
        'Patrimonio': (rangos['patrimonio'], cuentas_clasificadas['Patrimonio'])
    }

    for nombre_seccion, (rango, datos_seccion) in secciones_a_procesar.items():
        insertar_cuentas_en_rango(sheet, rango, datos_seccion, columnas, año_actual, año_anterior, nombre_seccion)

def procesar_hoja_analisis_vertical(sheet, cuentas_clasificadas, año_actual, año_anterior):
    """Procesa la hoja 'Análisis Vertical' reutilizando la lógica de la hoja comparativa."""
    # La lógica es idéntica, solo cambian los rangos que se obtienen de `obtener_rangos_fijos_por_hoja`
    procesar_hoja_comparativo(sheet, cuentas_clasificadas, año_actual, año_anterior)
