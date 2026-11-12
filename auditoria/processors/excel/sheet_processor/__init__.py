from ...shared.text_replacer import replace_text
from ..processor_anual_semestral import process_anual_semestral_sheets
from ..auxiliary_file import process_auxiliary_file_sheets
from ..comparative_actual_auxiliar import process_comparative_file
from ..materialidad_file import process_materialidad_file
from ..materialidad_nia320 import process_materialidad_nia320
from ..horizontal_vertical_analysis import process_horizontal_vertical_analysis
from ..analisis_hv_2026 import process_analisis_hv_2026
from ..initial_balance_tests import process_initial_balance_tests
from ..centralizadoras import process_centralizadora_file
from ..sumaria import process_sumaria_file
from ..importance_relativa import process_importance_relative
from ..ratios_financieros import process_ratios_financieros
from ..comparativo_saldos_2026 import (
    es_comparativo_registros,
    es_prueba_saldos_iniciales,
    process_comparativo_registros_2026,
    process_prueba_saldos_iniciales_2026,
)
from .normalizar_balances import normalizar_balances
from ....utils.replacements_utils import get_replacements_config
import os
import re
import unicodedata
import logging


logger = logging.getLogger(__name__)

# Plantillas 2026 de Análisis Financiero Preliminar. El árbol oficial las
# nombra '1_Analisis_Horizontal.xlsx' y '2_Analisis_Vertical_.xlsx' en
# Financiera y '2_Analisis_Vertical.xlsx' en Interna; versiones anteriores
# traían sufijos ('_1', '_1_1'). Se reconocen todas por patrón para que el
# escritor siga aplicándose aunque cambie el sufijo del archivo.
_PATRON_ANALISIS_HV = re.compile(
    r'^\d+[_\s]*analisis[_\s]*(horizontal|vertical)[_\s\d]*\.xlsx$',
    re.IGNORECASE,
)


def _leyenda_moneda_rota(valor, replacements):
    """
    Devuelve la leyenda de moneda en texto plano si *valor* es la fórmula rota
    que traen algunas plantillas oficiales, o None si no aplica.

    Varias cédulas sumarias incluyen
        =CONCATENATE("(Cifras expresadas en ",#REF!,")")
    porque la celda a la que apuntaban se borró al recortar la plantilla. Tal
    cual, Excel solo muestra #REF!, así que se escribe la leyenda resuelta.
    """
    if not valor.startswith('=') or '#REF!' not in valor:
        return None
    if 'cifras expresadas en' not in valor.lower():
        return None

    texto = replacements.get('[MONEDA_EXPRESION]')
    return f'({texto})' if texto else None


def _es_analisis_hv_2026(file_name):
    """True si el archivo es una plantilla de Análisis Horizontal/Vertical 2026."""
    normalizado = unicodedata.normalize('NFKD', file_name)
    normalizado = ''.join(c for c in normalizado if not unicodedata.combining(c))
    return bool(_PATRON_ANALISIS_HV.match(normalizado))


def _libro_tiene_hoja_sumaria(workbook):
    """
    True si alguna hoja del libro es una cédula sumaria.

    Los papeles de Revisoría agrupan varias cédulas en un mismo archivo y la
    sumaria no es la primera hoja ('B-SUM CÉDULA SUMARIA' es la tercera de
    3.2 INVERSIONES), así que el nombre del archivo no basta para reconocerla.
    """
    for hoja in workbook.worksheets:
        nombre = unicodedata.normalize('NFD', str(hoja.title or ''))
        nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn').upper()
        if 'SUMARIA' in nombre or '-SUM' in nombre:
            return True
    return False


# Encabezados que la plantilla rotula en una celda y deja el valor en la de al
# lado ('Entidad Auditada:' | <vacía>). El reemplazo por texto no los alcanza
# porque en esas plantillas no hay ningún hueco que sustituir: la celda del
# valor viene vacía. Es el caso de los papeles de Detección de Fraudes.
_ETIQUETAS_ENCABEZADO = {
    'entidad auditada': '[IDENTIDAD]',
    'entidad': '[IDENTIDAD]',
    'empresa': '[IDENTIDAD]',
    'entidad o empresa': '[IDENTIDAD]',
    'cliente': '[IDENTIDAD]',
    'razon social': '[IDENTIDAD]',
    'periodo auditado': '[FECHA_RANGO]',
    'periodo': '[FECHA_RANGO]',
    'ejercicio auditado': '[FECHA_RANGO]',
}

# Hueco propio de la plantilla: '[NOMBRE DEL CLIENTE]', '[EMPRESA]'... Es un
# marcador, no un dato del auditor, así que sí se sustituye.
_HUECO_PLANTILLA = re.compile(r'^\s*\[[^\]]+\]\s*$')


def _etiqueta_normalizada(valor):
    """'Entidad Auditada:' → 'entidad auditada'."""
    texto = unicodedata.normalize('NFD', str(valor))
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return ' '.join(texto.replace(':', ' ').lower().split())


def _rellenar_etiquetas_de_encabezado(sheet, replacements):
    """
    Escribe entidad y período en la celda contigua a su etiqueta cuando la
    plantilla la deja vacía. Nunca pisa un valor que ya venga escrito.
    """
    from openpyxl.cell.cell import MergedCell

    max_row = min(sheet.max_row or 1, 15)
    max_col = min(sheet.max_column or 1, 12)

    for fila in range(1, max_row + 1):
        for columna in range(1, max_col + 1):
            celda = sheet.cell(row=fila, column=columna)
            if not isinstance(celda.value, str) or ':' not in celda.value:
                continue

            clave = _ETIQUETAS_ENCABEZADO.get(_etiqueta_normalizada(celda.value))
            if not clave:
                continue

            texto = replacements.get(clave)
            if not texto:
                continue

            destino = sheet.cell(row=fila, column=columna + 1)
            if isinstance(destino, MergedCell):
                continue
            vacia = destino.value in (None, '')
            hueco = isinstance(destino.value, str) and _HUECO_PLANTILLA.match(destino.value)
            if not (vacia or hueco):
                continue
            destino.value = texto


def _actualizar_ejemplos_de_encabezado(sheet, replacements):
    """Rellena SOLO dos valores de demostración en cabeceras etiquetadas.

    Las plantillas productivas de Evaluación de Procesos traen en la fila 6
    nombres/ejercicios de ejemplo incluso cuando se actualizan A1..A3.
    No se modifican años del cuerpo, fórmulas o nombres de otras entidades.
    """
    from openpyxl.cell.cell import MergedCell

    labels = {
        "entidad auditada": (
            re.compile(r"^Empresa Auditada,\s*S\.?A\.?$", re.I),
            replacements.get("[IDENTIDAD]"),
        ),
        "periodo de auditoria": (
            re.compile(r"^Año terminado al\s+\d{1,2}\s+de\s+[a-záéíóú]+\s+de\s+\d{4}$", re.I),
            replacements.get("[FECHA_RANGO]"),
        ),
    }
    for fila in range(1, min(sheet.max_row or 1, 15) + 1):
        for columna in range(1, min(sheet.max_column or 1, 12) + 1):
            celda = sheet.cell(row=fila, column=columna)
            if not isinstance(celda.value, str) or not celda.value.strip().endswith(":"):
                continue
            etiqueta = _etiqueta_normalizada(celda.value)
            if etiqueta not in labels:
                continue
            patron, valor = labels[etiqueta]
            if not valor:
                continue
            for siguiente_col in range(columna + 1, min(columna + 4, (sheet.max_column or 1) + 1)):
                destino = sheet.cell(row=fila, column=siguiente_col)
                if isinstance(destino, MergedCell):
                    continue
                if isinstance(destino.value, str) and patron.fullmatch(destino.value.strip()):
                    destino.value = valor
                    break


def process_excel_sheets(workbook, tables_config, replacements, data_bd,
                         file_path=None, audit_id=None):
    """
    Procesa las hojas del Excel aplicando los reemplazos de texto

    Args:
        workbook: El libro de Excel a procesar
        tables_config: Configuración de las tablas
        replacements: Diccionario con los reemplazos a aplicar
        data_bd: Diccionario con los datos financieros
        file_path: Ruta completa al archivo Excel (opcional)
        audit_id: id de la auditoría, para rotular los cuadros comparativos con
            los años editables de `ParametrosAuditoria` (opcional)
    """
    # Extraer los componentes de data_bd en variables separadas
    balances = data_bd.get('balances', {})
    registros_auxiliares = data_bd.get('registros_auxiliares', {})
    saldos_iniciales = data_bd.get('saldos_iniciales', {})
    ajustes_reclasificaciones = data_bd.get('ajustes_reclasificaciones', {})

    # Reglas regex del encabezado (Entidad / Período / Moneda). Las plantillas
    # oficiales escriben esas líneas de formas ligeramente distintas, así que
    # el reemplazo literal no basta y se completa con estos patrones.
    reglas_regex = get_replacements_config().get('patrones_regex', [])

    # Procesar reemplazos normales en todas las hojas
    for sheet in workbook.worksheets:
        # Procesar reemplazos normales usando tables_config
        patrones_exactos = tables_config.get('patrones_exactos', {})

        # Procesar cada celda de la hoja para reemplazos
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value and isinstance(cell.value, str):
                    valor_original = cell.value.strip()

                    # Fórmulas rotas de la leyenda de moneda: la plantilla trae
                    # =CONCATENATE("(Cifras expresadas en ",#REF!,")"), que en
                    # Excel solo muestra #REF!. Se sustituye por el texto plano.
                    leyenda = _leyenda_moneda_rota(valor_original, replacements)
                    if leyenda:
                        cell.value = leyenda
                        continue

                    # Reemplazos exactos
                    if valor_original in patrones_exactos:
                        placeholder = patrones_exactos[valor_original]
                        if placeholder in replacements:
                            cell.value = replacements[placeholder]
                            continue

                    # Reemplazos de texto parciales + regex del encabezado
                    nuevo_valor = replace_text(valor_original, replacements, reglas_regex)
                    if nuevo_valor != valor_original:
                        cell.value = nuevo_valor

        # Encabezados rotulados ('Entidad Auditada:' + celda vacía al lado)
        _rellenar_etiquetas_de_encabezado(sheet, replacements)
        _actualizar_ejemplos_de_encabezado(sheet, replacements)

    if file_path:
        file_name = os.path.basename(file_path)

        # Para RATIOS FINANCIEROS, usamos los balances originales con sufijos de tipo_cuenta
        if file_name == "6 RATIOS FINANCIEROS.xlsx" and balances:
            logger.info(
                "Procesando RATIOS FINANCIEROS con balances originales (con sufijos tipo_cuenta)")
            workbook = process_ratios_financieros(workbook, balances)
        else:
            # Para todos los demás archivos, normalizamos los balances eliminando sufijos
            balances_normalizados = normalizar_balances(balances)
            if (file_name == "1 Estados Financieros Actuales y Anterior.xlsx" or
                    file_name == "19 Estados Financieros Actuales y Anterior.xlsx") and balances_normalizados:

                logger.info(
                    "Procesando Estados Financieros Actuales y Anterior con balances normalizados")
                logger.debug("Balances normalizados: %s",
                             balances_normalizados)
                workbook = process_anual_semestral_sheets(
                    workbook, balances_normalizados)
            elif file_name == "2 REGISTROS AUXILIARES.xlsx" and registros_auxiliares:
                workbook = process_auxiliary_file_sheets(
                    workbook, registros_auxiliares)
            elif file_name == "3 Comparativo Estados Financieros y Registros Auxiliares.xlsx" and balances_normalizados and registros_auxiliares:
                workbook = process_comparative_file(
                    workbook, balances_normalizados, registros_auxiliares)
            elif file_name == "8 MATERIALIDAD.xlsx" or file_name == "23 MATERIALIDAD.xlsx" and balances_normalizados:
                workbook = process_materialidad_file(
                    workbook, balances_normalizados)
            elif file_name == "Materialidad_NIA320.xlsx" and balances_normalizados:
                # NUEVA plantilla de materialidad (hoja 'Entrada de Datos' con
                # bases fijas): usa su escritor específico, no el antiguo.
                workbook = process_materialidad_nia320(
                    workbook, balances_normalizados, audit_id=audit_id)
            elif _es_analisis_hv_2026(file_name) and balances_normalizados:
                # Plantillas 2026: escritor específico (soporta 1 o 2 años)
                workbook = process_analisis_hv_2026(
                    workbook, balances_normalizados, file_name, audit_id=audit_id)
            elif (file_name == "4 ANÁLISIS HORIZONTAL DE BALANCE GENERAL.xlsx" or
                  file_name == "20 ANÁLISIS HORIZONTAL DE BALANCE GENERAL.xlsx" or
                  file_name == "5 ANÁLISIS VERTICAL DE BALANCE GENERAL.xlsx" or
                  file_name == "21 ANÁLISIS VERTICAL DE BALANCE GENERAL.xlsx") and balances_normalizados:
                workbook = process_horizontal_vertical_analysis(
                    workbook, balances_normalizados)
            elif es_comparativo_registros(file_name) and balances_normalizados:
                # Plantilla 2026: no pegaba los saldos de los Estados Financieros
                workbook = process_comparativo_registros_2026(
                    workbook, balances_normalizados, registros_auxiliares)
            elif es_prueba_saldos_iniciales(file_name) and balances_normalizados:
                # Plantilla 2026: no pegaba el saldo final/inicial de los períodos
                workbook = process_prueba_saldos_iniciales_2026(
                    workbook, balances_normalizados, saldos_iniciales)
            elif file_name == "6 Prueba de Saldos Iniciales.xlsx" and balances_normalizados and saldos_iniciales:
                workbook = process_initial_balance_tests(
                    workbook, balances_normalizados, saldos_iniciales)
            elif file_name.startswith("CENTRALIZADORA") and balances_normalizados:
                workbook = process_centralizadora_file(
                    workbook, balances_normalizados, ajustes_reclasificaciones,
                    file_name, audit_id=audit_id)
            elif ("SUMARIA" in file_name.upper()
                  or _libro_tiene_hoja_sumaria(workbook)) and balances_normalizados:
                # El nombre del archivo no siempre dice 'SUMARIA': en Revisoría
                # la cédula vive dentro del libro, en una hoja como
                # 'B-SUM CÉDULA SUMARIA' (tercera hoja de 3.2 INVERSIONES).
                workbook = process_sumaria_file(
                    workbook, balances_normalizados, ajustes_reclasificaciones,
                    file_name, audit_id=audit_id)
            elif "IMPORTANCIA RELATIVA" in file_name.upper() and balances_normalizados:
                workbook = process_importance_relative(
                    workbook, balances_normalizados, audit_id=audit_id)

    return workbook
