import re

def replace_text(text, replacements, regex_patterns=None):
    """
    Reemplaza texto con coincidencias simples y patrones regex dinámicos.
    
    Args:
        text (str): Texto original a procesar
        replacements (dict): Diccionario de reemplazos simples
        regex_patterns (list): Lista de patrones regex con claves a reemplazar (opcional)
    Returns:
        str: Texto con los reemplazos aplicados
    """
    # Reemplazo directo (case-insensitive)
    for key, value in replacements.items():
        if key.lower() in text.lower():
            text = text.replace(key, str(value))

    # Reemplazos por regex si están definidos
    if regex_patterns:
        for rule in regex_patterns:
            pattern = rule.get("pattern")
            key = rule.get("reemplazar_por")
            value = replacements.get(key)

            if pattern and value:
                # El valor se inserta con una lambda para que re.sub NO
                # interprete secuencias de escape del nombre de la entidad
                # (una entidad con '\' rompía el reemplazo).
                text = re.sub(pattern, lambda _m, v=str(value): v, text,
                              flags=re.IGNORECASE)
    return text
    