from ..shared.text_replacer import replace_text

def process_standard_text(doc, replacements, config):
    """
    Procesa el texto estándar en párrafos, encabezados y pies de página preservando estilos.
    Aplica tanto reemplazos directos como regex definidos en el JSON.
    Args:
        doc: Documento Word
        replacements: Diccionario de reemplazos simples
        config: Configuración completa del JSON, incluyendo 'patrones_regex'
    """
    regex_patterns = config.get("patrones_regex", [])

    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph, replacements, regex_patterns)

    for section in doc.sections:
        for header in section.header.paragraphs:
            replace_in_paragraph(header, replacements, regex_patterns)
        for footer in section.footer.paragraphs:
            replace_in_paragraph(footer, replacements, regex_patterns)


def replace_in_paragraph(paragraph, replacements, regex_patterns=None):
    """
    Reemplaza el texto de un párrafo preservando estilos, incluso si los patrones están repartidos en varios runs.
    """
    full_text = paragraph.text
    new_text = replace_text(full_text, replacements, regex_patterns)

    if full_text == new_text:
        return  # No hay cambios

    runs = paragraph.runs
    if not runs:
        return

    # Guardamos el primer run como base para aplicar estilo
    first_run = runs[0]
    for run in runs[1:]:
        paragraph._element.remove(run._element)  # eliminamos los demás

    first_run.text = new_text
