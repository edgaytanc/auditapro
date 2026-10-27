"""
Reglas de exclusión para el sistema de marcas de auditoría.

Define qué archivos/nombres NO deben recibir marcas de auditoría.
"""

EXCLUSION_KEYWORDS = {
    "PROGRAMA": {
        "reason": "Contiene hipervínculos críticos a otros documentos.",
        "severity": "strict",
        "applies_to": ["docx", "xlsx"],
    },
    "plantilla": {
        "reason": "Archivo de plantilla del sistema.",
        "severity": "strict",
        "applies_to": ["xlsx"],
    },
    "template": {
        "reason": "Archivo de plantilla del sistema.",
        "severity": "strict",
        "applies_to": ["xlsx", "docx"],
    },
    "_backup": {
        "reason": "Archivo de respaldo.",
        "severity": "strict",
        "applies_to": ["all"],
    },
    "config": {
        "reason": "Archivo de configuración del sistema.",
        "severity": "strict",
        "applies_to": ["all"],
    },
    "settings": {
        "reason": "Archivo de configuración del sistema.",
        "severity": "strict",
        "applies_to": ["all"],
    }
}

EXCLUSION_PREFIXES = {
    "~$": {
        "reason": "Archivo temporal de Excel/Word.",
        "severity": "strict",
        "applies_to": ["xlsx", "docx"]
    },
    ".": {
        "reason": "Archivo oculto del sistema.",
        "severity": "strict",
        "applies_to": ["all"]
    },
    "_temp": {
        "reason": "Archivo temporal.",
        "severity": "strict",
        "applies_to": ["all"]
    }
}

EXCLUSION_EXTENSIONS = {
    ".bak": "Archivo de respaldo",
    ".tmp": "Archivo temporal",
    ".log": "Archivo de registro",
    ".json": "Archivo de configuración JSON",
    ".xml": "Archivo de configuración XML",
    ".zip": "Archivo comprimido",
    ".rar": "Archivo comprimido"
}

EXCLUSION_EXACT_MATCHES = {}


def check_keyword_exclusion(text):
    """Verifica si el texto contiene alguna palabra clave de exclusión."""
    if not text:
        return (False, None, None)

    text_upper = text.upper()
    for keyword, config in EXCLUSION_KEYWORDS.items():
        if keyword.upper() in text_upper:
            return (True, config['reason'], config['severity'])

    return (False, None, None)


def check_prefix_exclusion(text):
    """Verifica si el texto comienza con algún prefijo de exclusión."""
    if not text:
        return (False, None)

    for prefix, config in EXCLUSION_PREFIXES.items():
        if text.startswith(prefix):
            return (True, config['reason'])

    return (False, None)


def check_extension_exclusion(text):
    """Verifica si el texto termina con alguna extensión de exclusión."""
    if not text:
        return (False, None)

    text_lower = text.lower()
    for ext, reason in EXCLUSION_EXTENSIONS.items():
        if text_lower.endswith(ext):
            return (True, reason)

    return (False, None)


def check_exact_exclusion(text):
    """Verifica si el texto coincide exactamente con algún patrón de exclusión."""
    if not text:
        return (False, None, None)

    text_upper = text.upper()
    for exact_text, config in EXCLUSION_EXACT_MATCHES.items():
        if text_upper == exact_text.upper():
            return (True, config['reason'], config.get('severity', 'warning'))

    return (False, None, None)


def is_excluded(text):
    """
    Verifica si el texto debe ser excluido según todas las reglas.

    Returns:
        dict: {'is_excluded': bool, 'reason': str, 'severity': str, 'rule_type': str}
    """
    if not text:
        return {
            'is_excluded': False,
            'reason': None,
            'severity': None,
            'rule_type': None
        }

    # Verificar palabra clave
    is_excl, reason, severity = check_keyword_exclusion(text)
    if is_excl:
        return {
            'is_excluded': True,
            'reason': reason,
            'severity': severity,
            'rule_type': 'keyword'
        }

    # Verificar prefijo
    is_excl, reason = check_prefix_exclusion(text)
    if is_excl:
        return {
            'is_excluded': True,
            'reason': reason,
            'severity': 'strict',
            'rule_type': 'prefix'
        }

    # Verificar extensión
    is_excl, reason = check_extension_exclusion(text)
    if is_excl:
        return {
            'is_excluded': True,
            'reason': reason,
            'severity': 'strict',
            'rule_type': 'extension'
        }

    # Verificar coincidencia exacta
    is_excl, reason, severity = check_exact_exclusion(text)
    if is_excl:
        return {
            'is_excluded': True,
            'reason': reason,
            'severity': severity,
            'rule_type': 'exact'
        }

    return {
        'is_excluded': False,
        'reason': None,
        'severity': None,
        'rule_type': None
    }
