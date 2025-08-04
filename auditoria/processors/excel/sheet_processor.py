from ..shared.text_replacer import replace_text
from .processor_anual_semestral import process_anual_semestral_sheets
from .auxiliary_file import process_auxiliary_file_sheets
from .comparative_actual_auxiliar import process_comparative_file
from .materialidad_file import process_materialidad_file
from .horizontal_vertical_analysis import process_horizontal_vertical_analysis
from .initial_balance_tests import process_initial_balance_tests
from .centralizadoras import process_centralizadora_file
from .sumaria_file import process_sumaria_file
from .importance_relative import process_importance_relative
from .ratios_financieros import process_ratios_financieros
import os

def process_excel_sheets(workbook, tables_config, replacements, data_bd, file_path=None):
    """
    Procesa las hojas del Excel aplicando los reemplazos de texto

    Args:
        workbook: El libro de Excel a procesar
        tables_config: Configuración de las tablas
        replacements: Diccionario con los reemplazos a aplicar
        data_bd: Diccionario con los datos financieros
        file_path: Ruta completa al archivo Excel (opcional)
    """
    # Extraer los componentes de data_bd en variables separadas
    balances = data_bd.get('balances', {})
    registros_auxiliares = data_bd.get('registros_auxiliares', {})
    saldos_iniciales = data_bd.get('saldos_iniciales', {})

    # Procesar reemplazos normales en todas las hojas
    for sheet in workbook.worksheets:
        print(f"\n Procesando reemplazos en hoja: {sheet.title}")

        # Procesar reemplazos normales usando tables_config
        patrones_exactos = tables_config.get('patrones_exactos', {})
        patrones_regex = tables_config.get('patrones_regex', {})

        # Procesar cada celda de la hoja para reemplazos
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    valor_original = cell.value.strip()

                    # Reemplazos exactos
                    if valor_original in patrones_exactos:
                        placeholder = patrones_exactos[valor_original]
                        if placeholder in replacements:
                            cell.value = replacements[placeholder]
                            continue

                    # Reemplazos de texto parciales
                    nuevo_valor = replace_text(valor_original, replacements)
                    if nuevo_valor != valor_original:
                        cell.value = nuevo_valor
                        continue

                    # Reemplazos con regex (si están definidos como diccionario)
                    if isinstance(patrones_regex, dict):
                        for patron, placeholder in patrones_regex.items():
                            if patron in valor_original and placeholder in replacements:
                                cell.value = valor_original.replace(
                                    patron, replacements[placeholder])
                                break

    if file_path:
        file_name = os.path.basename(file_path)
        if (file_name == "1 Estados Financieros Actuales y Anterior.xlsx" or
                file_name == "19 Estados Financieros Actuales y Anterior.xlsx") and balances:
            workbook = process_anual_semestral_sheets(workbook, balances)
        elif file_name == "2 REGISTROS AUXILIARES.xlsx" and registros_auxiliares:
            workbook = process_auxiliary_file_sheets(
                workbook, registros_auxiliares)
        elif file_name == "3 Comparativo Estados Financieros y Registros Auxiliares.xlsx" and balances and registros_auxiliares:
            workbook = process_comparative_file(
                workbook, balances, registros_auxiliares)
        elif file_name == "8 MATERIALIDAD.xlsx" or file_name == "23 MATERIALIDAD.xlsx" and balances:
            workbook = process_materialidad_file(workbook, balances)
        elif (file_name == "4 ANÁLISIS HORIZONTAL DE BALANCE GENERAL.xlsx" or
              file_name == "20 ANÁLISIS HORIZONTAL DE BALANCE GENERAL.xlsx" or
              file_name == "5 ANÁLISIS VERTICAL DE BALANCE GENERAL.xlsx" or
              file_name == "21 ANÁLISIS VERTICAL DE BALANCE GENERAL.xlsx") and balances:
            workbook = process_horizontal_vertical_analysis(workbook, balances)
        elif file_name == "6 Prueba de Saldos Iniciales.xlsx" and balances and saldos_iniciales:
            workbook = process_initial_balance_tests(
                workbook, balances, saldos_iniciales)
        elif file_name == "6 RATIOS FINANCIEROS.xlsx" and balances:
            workbook = process_ratios_financieros(workbook, balances)
        elif file_name.startswith("CENTRALIZADORA") and balances:
            workbook = process_centralizadora_file(
                workbook, balances, file_name)
        elif "SUMARIA" in file_name.upper() and balances:
            workbook = process_sumaria_file(workbook, balances, file_name)
        elif "IMPORTANCIA RELATIVA" in file_name.upper() and balances:
            workbook = process_importance_relative(workbook, balances)

    return workbook
