from docx import Document
from .processors.word import process_standard_text, process_tables
from .utils.replacements_utils import (
    get_replacements_config,
    get_tables_config,
    build_replacements_dict
)
import os

def modify_document_word(template_path, audit):
    """
    Modifica el documento Word con los datos de la auditoría
    """
    doc = Document(template_path)

    # Formatear las fechas usando los nombres correctos de los campos
    fecha_inicio = audit.fechaInit.strftime('%d de %B de %Y') if audit.fechaInit else '01 de Enero de 2024'
    fecha_fin = audit.fechaEnd.strftime('%d de %B de %Y') if audit.fechaEnd else '31 de Diciembre de 2024'

    # Convertir el mes a español
    meses = {
        'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
        'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
        'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
    }

    for eng, esp in meses.items():
        fecha_inicio = fecha_inicio.replace(eng, esp)
        fecha_fin = fecha_fin.replace(eng, esp)

    fecha_inicio_parts = fecha_inicio.split(' ')
    fecha_fin_parts = fecha_fin.split(' ')

    if len(fecha_inicio_parts) >= 4:
        fecha_inicio = f"{fecha_inicio_parts[0].zfill(2)} de {fecha_inicio_parts[2].capitalize()} de {fecha_inicio_parts[4]}"
    if len(fecha_fin_parts) >= 4:
        fecha_fin = f"{fecha_fin_parts[0].zfill(2)} de {fecha_fin_parts[2].capitalize()} de {fecha_fin_parts[4]}"

    # Cargar configuraciones
    replacements_config = get_replacements_config()
    tables_config = get_tables_config()

    # Construir reemplazos
    replacements = build_replacements_dict(replacements_config, audit, fecha_inicio, fecha_fin)

    # Procesar texto y tablas
    process_standard_text(doc, replacements, replacements_config)

    # Extraer el nombre del documento para los hipervínculos
    document_name = os.path.basename(template_path)
    process_tables(doc, replacements, tables_config, document_name, template_path, audit.id)
    
    return doc
