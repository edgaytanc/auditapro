"""
Vistas modularizadas para la aplicación de auditoría.
Importa todas las vistas desde los módulos especializados para mantener compatibilidad.
"""

# Importar vistas de descarga de documentos
from .download_views import (
    download_document,
    download_document_by_pattern
)

# Importar vistas de auditorías
from .audit_views import (
    auditorias_view,
    auditoria_financiera_view,
    auditoria_interna_view,
    auditoria_detalle_view,
    auditoria_revisoria_view
)

# Importar vistas del módulo de Muestreo NIA 530
from .muestreo_views import (
    muestreo_page,
    muestreo_calcular,
    muestreo_descargar
)

# Importar utilidades (disponibles para uso interno)
from .utils import (
    normalize_text,
    get_template_path,
    crear_mensaje_error,
    generar_html_estructura
)

# Exportar todas las vistas para compatibilidad hacia atrás
__all__ = [
    # Vistas de descarga
    'download_document',
    'download_document_by_pattern',
    
    # Vistas de auditorías
    'auditorias_view',
    'auditoria_financiera_view',
    'auditoria_interna_view',
    'auditoria_detalle_view',
    'auditoria_revisoria_view',

    # Vistas de muestreo NIA 530
    'muestreo_page',
    'muestreo_calcular',
    'muestreo_descargar',

    # Utilidades
    'normalize_text',
    'get_template_path',
    'crear_mensaje_error',
    'generar_html_estructura'
]
