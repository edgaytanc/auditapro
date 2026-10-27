"""
Paquete de mapeo de patrones de hipervínculos a rutas de archivos.
Proporciona funciones para convertir patrones como 'A-1', 'R-10' a rutas de archivos reales.
"""

# Importar las funciones principales para mantener compatibilidad
from .main_functions import get_file_info_from_pattern

# Importar todos los mapeos para acceso directo si es necesario
from .financial_audit_mappings import (
    PREFIX_TO_FOLDER,
    PATTERN_TO_FILE_A,
    PATTERN_TO_FILE_B,
    PATTERN_TO_FILE_C,
    PATTERN_TO_FILE_D,
    PATTERN_TO_FILE_E,
    PATTERN_TO_FILE_F,
    PATTERN_TO_FILE_G,
    PATTERN_TO_FILE_H,
    PATTERN_TO_FILE_I,
    PATTERN_TO_FILE_J,
    PATTERN_TO_FILE_R,
    PATTERN_TO_FILE,
)

from .internal_audit_mappings import (
    INTERNAL_PREFIX_TO_FOLDER,
    INTERNAL_PATTERN_TO_FILE_B,
    INTERNAL_PATTERN_TO_FILE_D,
    INTERNAL_PATTERN_TO_FILE_E,
    INTERNAL_PATTERN_TO_FILE_F,
    INTERNAL_PATTERN_TO_FILE_H,
    INTERNAL_PATTERN_TO_FILE_K,
    INTERNAL_PATTERN_TO_FILE_L,
    INTERNAL_PATTERN_TO_FILE_M,
    INTERNAL_PATTERN_TO_FILE_N,
    INTERNAL_PATTERN_TO_FILE_O,
    INTERNAL_PATTERN_TO_FILE_P,
    INTERNAL_PATTERN_TO_FILE_Q,
    INTERNAL_PREFIX_TO_PROGRAM,
    INTERNAL_PATTERN_TO_FILE,
)

from .special_patterns import (
    SPECIAL_PATTERNS,
    PREFIX_TO_PROGRAM,
)

__all__ = [
    'get_file_info_from_pattern',
    'PREFIX_TO_FOLDER',
    'PATTERN_TO_FILE',
    'INTERNAL_PREFIX_TO_FOLDER',
    'INTERNAL_PATTERN_TO_FILE',
    'SPECIAL_PATTERNS',
    'PREFIX_TO_PROGRAM',
    'INTERNAL_PREFIX_TO_PROGRAM',
]
