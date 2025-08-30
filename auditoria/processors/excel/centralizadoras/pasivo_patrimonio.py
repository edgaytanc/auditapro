from .base import (
    preparar_fechas_excel,
    insertar_fechas_en_celdas,
    buscar_fila_por_valor
)
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from openpyxl.utils import get_column_letter


def _mover_imagenes_por_insercion(sheet, start_row: int, delta_rows: int):
    """Mueve imágenes ancladas en filas >= start_row hacia abajo delta_rows.
    Soporta anclas como coordenada tipo 'A1' y anclas de uno/dos celdas.
    """
    if not hasattr(sheet, "_images") or delta_rows == 0:
        return

    for img in list(sheet._images):
        try:
            anchor = img.anchor
            # Caso 1: ancla como string 'A1'
            if isinstance(anchor, str):
                col_letters, row = coordinate_from_string(anchor)
                if row >= start_row:
                    new_row = row + delta_rows
                    img.anchor = f"{col_letters}{new_row}"
                continue

            # Caso 2: OneCellAnchor/TwoCellAnchor
            # openpyxl usa propiedades _from y (opcional) _to con .row/.col base 0
            if hasattr(anchor, "_from"):
                if anchor._from.row + 1 >= start_row:
                    anchor._from.row += delta_rows
                if hasattr(anchor, "_to") and anchor._to is not None:
                    if anchor._to.row + 1 >= start_row:
                        anchor._to.row += delta_rows
        except Exception:
            # No bloquear si alguna imagen tiene un anclaje no esperado
            continue


def insertar_datos_pasivo_patrimonio(workbook, cuentas_por_fecha, fechas_semestrales, ajustes_reclasificaciones):
    """
    Inserta datos en CENTRALIZADORA PASIVO-PATRIMONIO con ajustes.
    
    Estructura de columnas (según imagen):
    - D: Al 01/01/2023
    - E: Al 31/07/2023
    - F: Al 31/12/2023
    - G: Debe
    - H: Haber
    - I: Al 31/12/2024
    """
    sheet = workbook.active

    # 1. Preparar fechas
    fechas_año_viejo, fecha_mas_reciente, _, _, fechas_excel = preparar_fechas_excel(fechas_semestrales)
    insertar_fechas_en_celdas(sheet, fechas_excel)

    # 2. Obtener cuentas únicas de Pasivo y Patrimonio
    pasivo_cuentas = set()
    patrimonio_cuentas = set()
    
    for fecha, secciones in cuentas_por_fecha.items():
        if "Pasivo" in secciones:
            for cuenta in secciones["Pasivo"].keys():
                pasivo_cuentas.add(cuenta)
        if "Patrimonio" in secciones:
            for cuenta in secciones["Patrimonio"].keys():
                patrimonio_cuentas.add(cuenta)
    
    todas_cuentas = sorted(pasivo_cuentas) + sorted(patrimonio_cuentas)

    # 3. Determinar espacio disponible antes de la fila de suma y, si es necesario, insertar filas
    fila_inicio = 13
    suma_row_pre = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio')

    # Calcular filas necesarias vs. disponibles (si existe la fila de suma en la plantilla)
    if suma_row_pre:
        filas_disponibles = max(0, (suma_row_pre - 1) - fila_inicio)
        filas_necesarias = len(todas_cuentas)
        if filas_necesarias > filas_disponibles:
            faltantes = filas_necesarias - filas_disponibles
            sheet.insert_rows(suma_row_pre, faltantes)
            # Mover imágenes del pie hacia abajo para mantener posición relativa
            _mover_imagenes_por_insercion(sheet, suma_row_pre, faltantes)
            # Tras insertar, la fila de suma se desplaza hacia abajo
            suma_row_pre = suma_row_pre + faltantes

    # 4. Insertar datos por fila
    for i, cuenta in enumerate(todas_cuentas):
        fila_actual = fila_inicio + i
        
        # Nombre de la cuenta (columna B)
        sheet[f'B{fila_actual}'] = cuenta

        # Insertar saldos por fecha (columnas D, E, F, I)
        fechas_columnas = {
            'D': fechas_año_viejo[0],  # 01/01/2023
            'E': fechas_año_viejo[1],  # 31/07/2023
            'F': fechas_año_viejo[2],  # 31/12/2023
            'I': fecha_mas_reciente   # 31/12/2024
        }
        
        for col, fecha in fechas_columnas.items():
            seccion = "Pasivo" if cuenta in pasivo_cuentas else "Patrimonio"
            
            if fecha in cuentas_por_fecha and seccion in cuentas_por_fecha[fecha] and cuenta in cuentas_por_fecha[fecha][seccion]:
                sheet[f'{col}{fila_actual}'] = cuentas_por_fecha[fecha][seccion][cuenta]
            else:
                sheet[f'{col}{fila_actual}'] = 0

        # Insertar ajustes (columnas G=Debe, H=Haber)
        sheet[f'G{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('debe', 0)
        sheet[f'H{fila_actual}'] = ajustes_reclasificaciones.get(cuenta, {}).get('haber', 0)

    # 5. Asegurar y actualizar la fila de suma
    if todas_cuentas:
        last_row = fila_inicio + len(todas_cuentas) - 1
        suma_target_row = last_row + 1

        # Localizar la fila de suma (puede haber sido desplazada por insert_rows)
        suma_row = buscar_fila_por_valor(sheet, 'B', 'Suma Pasivo y Patrimonio')

        if not suma_row:
            # No existía en la plantilla: crearla
            suma_row = suma_target_row
            sheet[f'B{suma_row}'] = 'Suma Pasivo y Patrimonio'
        elif suma_row != suma_target_row:
            # Mover a la posición correcta por seguridad
            sheet.move_range(f"A{suma_row}:I{suma_row}", rows=(suma_target_row - suma_row))
            suma_row = suma_target_row
        
        # Actualizar fórmulas de suma (columnas D-I)
        for col in ['D', 'E', 'F', 'G', 'H', 'I']:
            sheet[f"{col}{suma_row}"] = f"=SUM({col}{fila_inicio}:{col}{last_row})"