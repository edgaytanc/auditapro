"""
Módulo de configuración para el sistema de auditoría
"""
from .exclusion_rules import (
    is_excluded,
    check_keyword_exclusion,
    check_prefix_exclusion,
    check_extension_exclusion,
    check_exact_exclusion,
    EXCLUSION_KEYWORDS,
    EXCLUSION_PREFIXES,
    EXCLUSION_EXTENSIONS,
    EXCLUSION_EXACT_MATCHES
)

__all__ = [
    'is_excluded',
    'check_keyword_exclusion',
    'check_prefix_exclusion',
    'check_extension_exclusion',
    'check_exact_exclusion',
    'EXCLUSION_KEYWORDS',
    'EXCLUSION_PREFIXES',
    'EXCLUSION_EXTENSIONS',
    'EXCLUSION_EXACT_MATCHES'
]
