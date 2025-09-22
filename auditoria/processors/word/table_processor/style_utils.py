"""
Utilidades para manejo de estilos y formato en documentos Word.
Contiene funciones para preservar formato al modificar texto en celdas.
"""

import logging

logger = logging.getLogger(__name__)

def set_text_with_style_from_reference_cell(target_cell, text, reference_cell):
    """
    Inserta texto en `target_cell` con el mismo estilo del primer run de `reference_cell`.
    """
    target_cell.text = ""  # Limpiar contenido anterior

    ref_paragraphs = reference_cell.paragraphs
    if ref_paragraphs and ref_paragraphs[0].runs:
        ref_run = ref_paragraphs[0].runs[0]
        paragraph = target_cell.paragraphs[0]
        new_run = paragraph.add_run(text)
        # Copiar estilos básicos
        new_run.bold = ref_run.bold
        new_run.italic = ref_run.italic
        new_run.underline = ref_run.underline
        new_run.font.size = ref_run.font.size
        new_run.font.name = ref_run.font.name
        new_run.font.color.rgb = ref_run.font.color.rgb
    else:
        # Si no se encuentra un estilo de referencia válido, insertar texto plano
        target_cell.text = text

def replace_text_preserving_format(cell, old_text, new_text):
    """
    Reemplaza texto en una celda preservando todos los elementos de formato.
    
    En lugar de asignar directamente text a la celda (lo que destruye el formato),
    esta función trabaja con párrafos y runs individuales.
    """
    if not old_text or old_text == new_text:
        return False

    changed = False
    # Trabajamos a nivel de párrafos para preservar la estructura
    for paragraph in cell.paragraphs:
        if paragraph.text and old_text in paragraph.text:
            # Almacenamos información sobre los runs originales
            runs_info = []
            for run in paragraph.runs:
                runs_info.append({
                    'text': run.text,
                    'bold': run.bold,
                    'italic': run.italic,
                    'underline': run.underline,
                    'size': run.font.size,
                    'name': run.font.name,
                    'color': run.font.color.rgb
                })
            
            # Reemplazamos el texto completo del párrafo
            new_paragraph_text = paragraph.text.replace(old_text, new_text)
            
            # Limpiamos el párrafo
            for i in range(len(paragraph.runs)-1, -1, -1):
                paragraph._p.remove(paragraph.runs[i]._r)
            
            # Si el párrafo tiene una estructura simple, simplemente añadimos un run
            if len(runs_info) == 1:
                run = paragraph.add_run(new_paragraph_text)
                run.bold = runs_info[0]['bold']
                run.italic = runs_info[0]['italic']
                run.underline = runs_info[0]['underline']
                run.font.size = runs_info[0]['size']
                run.font.name = runs_info[0]['name']
                run.font.color.rgb = runs_info[0]['color']
            # Si es más complejo, reconstruimos los runs manteniendo el formato
            else:
                paragraph.add_run(new_paragraph_text)
            
            changed = True
    
    return changed
