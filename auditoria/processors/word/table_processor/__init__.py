"""
Procesador de tablas modularizado para documentos Word.
Función principal para procesar y reemplazar texto en tablas con soporte para hipervínculos.
"""

import logging
import re
from ...shared.text_replacer import replace_text
from .style_utils import set_text_with_style_from_reference_cell, replace_text_preserving_format
from .hyperlink_processor import apply_hyperlinks_to_document
from .nomenclature_config import get_nomenclature_config

logger = logging.getLogger(__name__)

def process_tables(doc, replacements, tables_config=None, document_name=None, document_path=None, audit_id=None):
    """
    Procesa y reemplaza texto en tablas de un documento Word.
    
    Args:
        doc: Documento Word a procesar
        replacements: Diccionario con los valores a reemplazar
        tables_config: Configuración específica para tablas (opcional)
        document_name: Nombre del documento (para hipervínculos)
        document_path: Ruta del documento (para hipervínculos)
        audit_id: ID de la auditoría (para hipervínculos)
        
    Returns:
        Documento Word procesado
    """
    patrones = tables_config.get("patrones", [])
    patrones_regex = tables_config.get("patrones_regex", [])
    processed_cells = {}  # Diccionario para rastrear celdas ya procesadas
    is_programa_document = "1 programa" in document_name.lower()

    for idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                # Generar un ID único para esta celda
                cell_id = f"table_{idx}_row_{row_idx}_col_{col_idx}"
                
                # Si la celda ya fue procesada, continuamos con la siguiente
                if cell_id in processed_cells:
                    continue
                    
                cell_text = cell.text.strip().replace('\n', ' ').replace('  ', ' ')

                # Para documentos "1 PROGRAMA", ejecutar Caso 3 (regex) PRIMERO con prioridad absoluta
                if is_programa_document and patrones_regex:
                    texto_original = cell.text
                    patrones_aplicados = set()
                    
                    for patron_regex in patrones_regex:
                        pattern = patron_regex.get("pattern")
                        key = patron_regex.get("reemplazar_por")
                        
                        patron_id = f"{pattern}_{key}"
                        if patron_id in patrones_aplicados:
                            continue
                            
                        valor = replacements.get(key, "")
                        
                        if pattern and valor and cell.text:
                            match = re.search(pattern, cell.text)
                            if match:
                                patrones_aplicados.add(patron_id)
                                # Para patrones que terminan en \\s*$, agregar el valor después del patrón
                                if pattern.endswith("\\s*$"):
                                    # Reemplazar el patrón manteniendo la etiqueta y agregando el valor
                                    matched_text = match.group(0)
                                    # Extraer la etiqueta (ej: "Entidad:", "Auditoría:")
                                    label = matched_text.rstrip()
                                    new_text = f"{label} {valor}"
                                    replace_text_preserving_format(cell, matched_text, new_text)
                                else:
                                    # Comportamiento original para otros patrones
                                    matched_text = cell.text[match.start():match.end()]
                                    replace_text_preserving_format(cell, matched_text, valor)
                                processed_cells[cell_id] = True
                    
                    # Si ya se procesó con regex, continuar con la siguiente celda
                    if cell_id in processed_cells:
                        continue

                # Para documentos que NO son "1 PROGRAMA", usar el flujo normal
                if not is_programa_document:
                    # Caso 1: reemplazo en celda adyacente con estilo
                    for patron in patrones:
                        buscar = patron.get("buscar")
                        clave = patron.get("valor")
                        valor = replacements.get(clave, "")

                        if cell_text == buscar:
                            try:
                                next_cell = row.cells[col_idx + 1]
                                next_cell_id = f"table_{idx}_row_{row_idx}_col_{col_idx + 1}"
                                set_text_with_style_from_reference_cell(next_cell, valor, cell)
                                processed_cells[cell_id] = processed_cells[next_cell_id] = True
                            except IndexError:
                                pass

                    # Si la celda ya fue procesada, saltamos los otros casos
                    if cell_id in processed_cells:
                        continue

                    # Caso 2: reemplazo parcial dentro de la misma celda (directo)
                    for patron in patrones:
                        buscar = patron.get("buscar")
                        if buscar in cell_text:
                            nuevo_texto = replace_text(cell_text, replacements)
                            if nuevo_texto != cell_text:
                                replace_text_preserving_format(cell, cell_text, nuevo_texto)
                                processed_cells[cell_id] = True
                    
                    # Caso 3: aplicar reemplazos regex desde JSON para documentos normales
                    if not cell_id in processed_cells and patrones_regex:
                        texto_original = cell.text
                        patrones_aplicados = set()
                        
                        for patron_regex in patrones_regex:
                            pattern = patron_regex.get("pattern")
                            key = patron_regex.get("reemplazar_por")
                            
                            patron_id = f"{pattern}_{key}"
                            if patron_id in patrones_aplicados:
                                continue
                                
                            valor = replacements.get(key, "")
                            
                            if pattern and valor and cell.text:
                                match = re.search(pattern, cell.text)
                                if match:
                                    patrones_aplicados.add(patron_id)
                                    # Para patrones que terminan en \\s*$, agregar el valor después del patrón
                                    if pattern.endswith("\\s*$"):
                                        # Reemplazar el patrón manteniendo la etiqueta y agregando el valor
                                        matched_text = match.group(0)
                                        # Extraer la etiqueta (ej: "Entidad:", "Auditoría:")
                                        label = matched_text.rstrip()
                                        new_text = f"{label} {valor}"
                                        replace_text_preserving_format(cell, matched_text, new_text)
                                    else:
                                        # Comportamiento original para otros patrones
                                        matched_text = cell.text[match.start():match.end()]
                                        replace_text_preserving_format(cell, matched_text, valor)
                                    processed_cells[cell_id] = True
    
    # Aplicar hipervínculos si hay información suficiente
    if audit_id and document_name:
        # Obtener la configuración de nomenclatura
        nomenclature_config = get_nomenclature_config(document_name, document_path)
        doc = apply_hyperlinks_to_document(doc, audit_id, document_name, document_path, nomenclature_config)

    return doc

# Exportar las funciones principales para compatibilidad hacia atrás
__all__ = [
    'process_tables',
    'get_nomenclature_config',
    'apply_hyperlinks_to_document',
    'set_text_with_style_from_reference_cell',
    'replace_text_preserving_format'
]
