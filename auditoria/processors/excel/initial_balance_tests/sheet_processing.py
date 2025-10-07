import logging
import re
from copy import copy

logger = logging.getLogger(__name__)

def actualizar_fechas_encabezados(sheet, fecha_balance, fecha_saldos_iniciales):
    """Actualiza las fechas en los encabezados de las columnas"""
    # Formatear fecha balance (31/12/YYYY)
    if fecha_balance:
        partes_fecha = fecha_balance.split('-')
        fecha_balance_formateada = f"{partes_fecha[2]}/{partes_fecha[1]}/{partes_fecha[0]}" if len(partes_fecha) == 3 else fecha_balance
    else:
        fecha_balance_formateada = "31/12/AAAA"
    
    # Formatear fecha saldos iniciales (01/01/YYYY)
    try:
        if fecha_saldos_iniciales and '-' in fecha_saldos_iniciales and len(fecha_saldos_iniciales.split('-')) == 3:
            fecha_saldos_formateada = f"01/01/{fecha_saldos_iniciales.split('-')[0]}"
        else:
            año_balance = int(fecha_balance.split('-')[0]) if fecha_balance else 0
            fecha_saldos_formateada = f"01/01/{año_balance + 1}"
    except (ValueError, IndexError):
        fecha_saldos_formateada = "01/01/AAAA"
    
    # Buscar y reemplazar fechas en los encabezados
    for row_idx in range(1, 50):
        for col_idx in range(1, 10):
            if cell_value := sheet.cell(row=row_idx, column=col_idx).value:
                if isinstance(cell_value, str):
                    if "31/12/AAAA" in cell_value:
                        sheet.cell(row=row_idx, column=col_idx).value = cell_value.replace("31/12/AAAA", fecha_balance_formateada)
                    
                    if "01/01/AAAA" in cell_value:
                        sheet.cell(row=row_idx, column=col_idx).value = cell_value.replace("01/01/AAAA", fecha_saldos_formateada)

def buscar_fila_encabezado(sheet):
    """Busca la fila de encabezado en la hoja donde se insertarán los datos"""
    for row_idx in range(1, 50):
        for col_idx in range(1, 10):
            if cell_value := sheet.cell(row=row_idx, column=col_idx).value:
                if isinstance(cell_value, str) and any(term in cell_value.lower() for term in ["cuenta", "descripción"]):
                    return row_idx
    return None

def insertar_datos_en_hoja(sheet, fila_encabezado, cuentas_balance, cuentas_saldos_iniciales, fecha_ultimo_dia):
    """Inserta los datos de balances y saldos iniciales en la hoja"""
    # Buscar la tabla "Evaluación de Saldos Iniciales"
    fila_tabla = next((row_idx for row_idx in range(1, 50) 
                      for col_idx in range(1, 15) 
                      if isinstance(sheet.cell(row=row_idx, column=col_idx).value, str) 
                      and "evaluación de saldos iniciales" in sheet.cell(row=row_idx, column=col_idx).value.lower()), None)
    
    if not fila_tabla:
        return
    
    # Buscar fila de encabezados
    fila_encabezados = next((i for i in range(fila_tabla, fila_tabla + 5)
                           for col_idx in range(1, 15)
                           if isinstance(sheet.cell(row=i, column=col_idx).value, str)
                           and "cuenta" in sheet.cell(row=i, column=col_idx).value.lower()), None)
    
    if not fila_encabezados:
        return
    
    # Buscar columnas específicas
    col_cuenta = encontrar_columna_por_texto(sheet, fila_encabezados, ["cuenta"])
    col_saldo_final = encontrar_columna_por_texto(sheet, fila_encabezados, ["segùnfinal", "según final", "31/12"])
    col_saldo_inicial = encontrar_columna_por_texto(sheet, fila_encabezados, ["saldo incial", "s/contabilidad al", "01/01"])
    
    if not (col_cuenta and col_saldo_inicial and col_saldo_final):
        return
    
    # Combinar todas las cuentas de balance para procesarlas
    todas_las_cuentas = [(seccion, cuenta) for seccion in ["Activo", "Pasivo", "Patrimonio", "ESTADO DE RESULTADOS"]
                        if seccion in cuentas_balance
                        for cuenta in cuentas_balance[seccion]
                        if "inversiones" not in cuenta.lower()]
    
    if not todas_las_cuentas:
        return
    
    # Configurar inserción en fila 29
    fila_inicial = 29
    filas_disponibles = sum(1 for i in range(fila_inicial, 35) if sheet.cell(row=i, column=col_cuenta).value is None)
    filas_adicionales_necesarias = max(0, len(todas_las_cuentas) - filas_disponibles)
    
    # Insertar filas adicionales si es necesario
    if filas_adicionales_necesarias > 0:
        # Guardar las fórmulas y valores de las filas que se pueden usar como plantilla
        fila_plantilla = 34
        formulas_y_valores = {}
        
        # Capturar todas las fórmulas y valores de la fila plantilla
        for col in range(1, sheet.max_column + 1):
            celda = sheet.cell(row=fila_plantilla, column=col)
            if celda.value is not None:
                # Guardar la fórmula si existe
                if celda.data_type == 'f':
                    formulas_y_valores[col] = {'formula': celda.value, 'tipo': 'formula'}
                else:
                    formulas_y_valores[col] = {'valor': celda.value, 'tipo': 'valor'}
        
        # Insertar las filas nuevas
        sheet.insert_rows(35, filas_adicionales_necesarias)
        
        # Copiar estilos y fórmulas a las nuevas filas
        for i in range(filas_adicionales_necesarias):
            fila_destino = 35 + i
            for col in range(1, sheet.max_column + 1):
                try:
                    celda_destino = sheet.cell(row=fila_destino, column=col)
                    celda_origen = sheet.cell(row=fila_plantilla, column=col)
                    
                    # Copiar el estilo
                    copiar_estilo(celda_origen, celda_destino)
                    
                    # Aplicar fórmulas o valores si existen en la plantilla
                    if col in formulas_y_valores:
                        if formulas_y_valores[col]['tipo'] == 'formula':
                            # Ajustar la referencia de fila en la fórmula si es necesario
                            formula = formulas_y_valores[col]['formula']
                            # Reemplazar referencias de fila si la fórmula contiene referencias a celdas
                            if isinstance(formula, str) and formula.startswith('='):
                                # Ajustar la fórmula para la nueva fila
                                formula_ajustada = ajustar_formula_para_nueva_fila(formula, fila_plantilla, fila_destino)
                                celda_destino.value = formula_ajustada
                        elif formulas_y_valores[col]['tipo'] == 'valor' and col != col_cuenta and col != col_saldo_final and col != col_saldo_inicial:
                            # Solo copiar valores que no sean de las columnas que se llenarán con datos
                            celda_destino.value = formulas_y_valores[col]['valor']
                except Exception as e:
                    logger.error(f"Error al copiar estilo o fórmula: {str(e)}")
    
    # Insertar los datos
    fila_actual = fila_inicial
    for idx, (seccion, cuenta) in enumerate(todas_las_cuentas):
        if idx >= 100:  # Límite de 100 cuentas
            break
            
        sheet.cell(row=fila_actual, column=col_cuenta).value = cuenta
        sheet.cell(row=fila_actual, column=col_saldo_final).value = cuentas_balance[seccion][cuenta]
        
        if cuenta in cuentas_saldos_iniciales:
            sheet.cell(row=fila_actual, column=col_saldo_inicial).value = cuentas_saldos_iniciales[cuenta]
        
        fila_actual += 1

def copiar_estilo(celda_origen, celda_destino):
    """Copia el estilo completo de una celda a otra"""
    if celda_origen is None or celda_destino is None:
        return
        
    for attr in ['font', 'fill', 'border', 'alignment', 'number_format']:
        if hasattr(celda_origen, attr) and getattr(celda_origen, attr):
            setattr(celda_destino, attr, copy(getattr(celda_origen, attr)))

def encontrar_columna_por_texto(sheet, fila, textos_buscar):
    """Encuentra el número de columna que contiene alguno de los textos especificados"""
    for col_idx in range(1, sheet.max_column + 1):
        if cell_value := sheet.cell(row=fila, column=col_idx).value:
            if isinstance(cell_value, str):
                cell_value_lower = cell_value.lower()
                if any(texto.lower() in cell_value_lower for texto in textos_buscar):
                    return col_idx
    return None

def ajustar_formula_para_nueva_fila(formula, fila_origen, fila_destino):
    """Ajusta las referencias de fila en una fórmula para una nueva fila"""
    if not isinstance(formula, str) or not formula.startswith('='):
        return formula
    
    # Diferencia entre filas
    diferencia = fila_destino - fila_origen
    
    # Patrón para encontrar referencias de celda (ej: A34, $B$34, C34:D34)
    patron_celda = re.compile(r'([A-Z]+\$?)(\d+)')
    
    def reemplazar_fila(match):
        columna, fila = match.groups()
        # No ajustar si la fila tiene un $ (referencia absoluta)
        if '$' in fila:
            return match.group(0)
        # Ajustar la fila sumando la diferencia
        nueva_fila = int(fila) + diferencia
        return f"{columna}{nueva_fila}"
    
    # Reemplazar todas las referencias de celda en la fórmula
    formula_ajustada = patron_celda.sub(reemplazar_fila, formula)
    return formula_ajustada
