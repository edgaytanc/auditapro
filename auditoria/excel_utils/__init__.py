"""
Utilidades modularizadas para procesamiento de documentos Excel.
Funciones principales para modificar documentos Excel normales y con macros.
"""

from openpyxl import load_workbook
from .date_formatter import format_audit_dates
from .xlsm_processor import modify_document_excel_with_macros
from ..processors.excel.sheet_processor import process_excel_sheets
from ..utils.replacements_utils import (
    get_replacements_config,
    get_tables_config,
    build_replacements_dict,
)
from ..utils.data_db import get_all_financial_data

def modify_document_excel(template_path, audit):
    """
    Modifica un documento Excel (.xlsx) aplicando reemplazos y procesando hojas.
    
    Args:
        template_path: Ruta al archivo Excel template
        audit: Objeto Audit con los datos para reemplazar
        
    Returns:
        Workbook: Objeto openpyxl Workbook procesado
    """
    wb = load_workbook(template_path)

    # Formatear fechas de auditoría
    fecha_inicio, fecha_fin = format_audit_dates(audit)

    # Obtener datos financieros
    financial_data = get_all_financial_data(audit.id)
    data_bd = financial_data['organized']
    
    # Obtener configuraciones
    replacements_config = get_replacements_config()
    tables_config = get_tables_config()
    
    # Obtener los reemplazos básicos
    replacements = build_replacements_dict(
        config=replacements_config,
        audit=audit,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    
    print(data_bd)
    
    # Procesar el documento Excel
    process_excel_sheets(wb, tables_config, replacements, data_bd, template_path)
    
    return wb

# Exportar las funciones principales para compatibilidad hacia atrás
__all__ = [
    'modify_document_excel',
    'modify_document_excel_with_macros',
    'format_audit_dates'
]
