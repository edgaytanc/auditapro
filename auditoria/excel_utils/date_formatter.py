"""
Utilidades para formateo de fechas en documentos Excel.
Contiene funciones para formatear fechas de auditoría y traducir meses.
"""

# Diccionario de traducción de meses inglés-español
MONTH_TRANSLATIONS = {
    'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
    'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
    'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
}

def format_audit_dates(audit):
    """
    Formatea las fechas de inicio y fin de una auditoría.

    Args:
        audit: Objeto Audit con fechaInit y fechaEnd
        
    Returns:
        tuple: (fecha_inicio_formateada, fecha_fin_formateada)
    """
    fecha_inicio = audit.fechaInit.strftime('%d de %B de %Y') if audit.fechaInit else '01 de Enero de 2024'
    fecha_fin = audit.fechaEnd.strftime('%d de %B de %Y') if audit.fechaEnd else '31 de Diciembre de 2024'
    
    # Traducir nombres de meses a español
    for eng, esp in MONTH_TRANSLATIONS.items():
        fecha_inicio = fecha_inicio.replace(eng, esp)
        fecha_fin = fecha_fin.replace(eng, esp)
    
    # Formatear fechas con ceros a la izquierda y capitalización
    fecha_inicio = _format_date_parts(fecha_inicio)
    fecha_fin = _format_date_parts(fecha_fin)
    
    return fecha_inicio, fecha_fin

def _format_date_parts(fecha_str):
    """
    Formatea las partes de una fecha para asegurar formato consistente.
    
    Args:
        fecha_str: Fecha en formato "DD de MMMM de YYYY"
        
    Returns:
        str: Fecha formateada con ceros a la izquierda y capitalización
    """
    parts = fecha_str.split(' ')
    
    if len(parts) >= 4:
        day = parts[0].zfill(2)  # Agregar cero a la izquierda si es necesario
        month = parts[2].capitalize()  # Capitalizar el mes
        year = parts[4]
        return f"{day} de {month} de {year}"
    
    return fecha_str
