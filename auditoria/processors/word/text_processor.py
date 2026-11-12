from ..shared.text_replacer import replace_text
from difflib import SequenceMatcher

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

    # El procesador productivo eliminaba todos los runs salvo el primero.
    # Eso convertía títulos y valores con estilos distintos en un solo run.
    # Conservar cada run y reasignar únicamente el tramo modificado.
    origen = "".join(run.text for run in runs)
    if origen != full_text:
        # No arriesgar la pérdida de hipervínculos o campos que no estén en
        # paragraph.runs. Esos elementos requieren su propio procesador.
        return

    positions = []
    for i, run in enumerate(runs):
        positions.extend([i] * len(run.text))
    partes = ["" for _ in runs]
    diferencia = SequenceMatcher(None, full_text, new_text, autojunk=False)
    for operacion, desde, hasta, nuevo_desde, nuevo_hasta in diferencia.get_opcodes():
        if operacion == "equal":
            for j in range(desde, hasta):
                partes[positions[j]] += full_text[j]
        elif operacion in ("replace", "insert"):
            destino = positions[desde] if desde < len(positions) else len(runs) - 1
            partes[destino] += new_text[nuevo_desde:nuevo_hasta]
        # Las eliminaciones no se copian.

    for run, contenido in zip(runs, partes):
        if run.text != contenido:
            run.text = contenido
