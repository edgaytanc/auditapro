import re

# Únicamente títulos del encabezado; dentro de un párrafo narrativo son texto
# legítimo y no deben convertirse en el título del encargo.
_TITULOS_DOCUMENTO = {
    "auditoria financiera", "auditoría financiera",
    "auditoria de estados financieros", "auditoría de estados financieros",
    "auditoria de procesos", "auditoría de procesos",
}
_ETIQUETAS_SOLO_VACIAS = {
    "entidad:", "auditoría:", "auditoria:", "período:", "periodo:",
}
_CLAVES_REGEX_SOLO_VACIAS = {
    "[ENTIDAD_COMPLETA]", "[AUDITORIA_COMPLETA]", "[FECHA_RANGO_COMPLETA]",
}


def replace_text(text, replacements, regex_patterns=None):
    """Aplica las reglas productivas sin sobrescribir campos YA rellenados.

    Conserva los marcadores explícitos y las expresiones de encabezado. En
    cambio, una etiqueta como ``Gerente de Auditoría: CPA ...`` no es un hueco.
    Protege asimismo las descripciones y referencias históricas del documento.
    """
    if not isinstance(text, str) or not text:
        return text

    for key, value in replacements.items():
        if not isinstance(key, str) or not key:
            continue
        normalized = key.strip().casefold()
        if normalized in _ETIQUETAS_SOLO_VACIAS or normalized in _TITULOS_DOCUMENTO:
            if text.strip().casefold() != normalized:
                continue
        if key in text:
            text = text.replace(key, str(value))

    if regex_patterns:
        for rule in regex_patterns:
            pattern = rule.get("pattern")
            key = rule.get("reemplazar_por")
            value = replacements.get(key)
            if not pattern or value is None or value == "":
                continue
            # Productivo admite etiquetas aisladas, no etiquetas seguidas por
            # un valor existente ni etiquetas que sean parte de otra frase.
            if key in _CLAVES_REGEX_SOLO_VACIAS and (
                text.strip().casefold() not in _ETIQUETAS_SOLO_VACIAS
            ):
                continue
            text = re.sub(pattern, lambda _match, v=str(value): v, text,
                          flags=re.IGNORECASE)
    return text
