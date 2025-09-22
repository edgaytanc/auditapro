"""
Configuración de nomenclatura para documentos Word.
Contiene la lógica para determinar prefijos y rangos basados en nombres de documentos y rutas.
"""

import logging
from .financial_audit_mappings import FINANCIAL_NOMENCLATURE_MAP
from .internal_audit_mappings import INTERNAL_NOMENCLATURE_MAP, INTERNAL_PATH_TO_PREFIX_MAP

logger = logging.getLogger(__name__)

def get_nomenclature_config(document_name, document_path=None):
    """
    Devuelve la configuración de nomenclatura para un documento en particular.
    
    Args:
        document_name: Nombre del documento (sin ruta)
        document_path: Ruta completa del documento, necesaria para mapeos basados en ruta
    
    Returns:
        dict: Configuración de nomenclatura con prefix y max_range o None si no coincide
    """
    # Primero intentamos con la configuración existente
    document_name_lower = document_name.lower()
    
    # Verificar primero en el mapa estándar
    config = FINANCIAL_NOMENCLATURE_MAP.get(document_name_lower)
    if config:
        return config
    
    # Si no se encontró y tenemos la ruta del documento, verificamos en la estructura de auditoría interna
    if document_path and "programa de auditor" in document_name.lower():
        # Normalizar la ruta para la búsqueda
        normalized_path = document_path.replace('\\', '/').lower()
        
        # Verificar si la ruta contiene "6 AUDITORIA DE PROCESOS"
        if "6 auditoria de procesos" in normalized_path:
            
            # Primero intentamos la coincidencia directa por patrones de ruta
            for pattern, prefix in INTERNAL_PATH_TO_PREFIX_MAP.items():
                if pattern in normalized_path:
                    max_range = 12  # Valor estándar para todos
                    config = {"prefix": prefix, "max_range": max_range}
                    return config
            
            # Si no encontramos coincidencia directa, buscamos por áreas específicas
            for area_name, area_config in INTERNAL_NOMENCLATURE_MAP["6 AUDITORIA DE PROCESOS"].items():
                area_pattern = area_name.lower()
                if area_pattern in normalized_path:
                    
                    # Verificar si el área tiene subáreas o documentos directamente
                    if isinstance(next(iter(area_config.values())), dict):
                        # El área tiene subáreas
                        # Verificar si alguna subárea está en la ruta
                        for subarea_name, subarea_config in area_config.items():
                            if subarea_name.lower() in normalized_path:
                                
                                # Verificar si el documento coincide
                                for doc_name, doc_config in subarea_config.items():
                                    doc_name_clean = doc_name.lower().replace('í', 'i').replace('á', 'a')
                                    doc_search = document_name.lower().replace('í', 'i').replace('á', 'a')
                                    
                                    if doc_name_clean in doc_search:
                                        return doc_config
                    else:
                        # El área tiene documentos directamente (sin subáreas)
                        for doc_name, doc_config in area_config.items():
                            doc_name_clean = doc_name.lower().replace('í', 'i').replace('á', 'a')
                            doc_search = document_name.lower().replace('í', 'i').replace('á', 'a')
                            
                            if doc_name_clean in doc_search:
                                return doc_config
    
    return None
