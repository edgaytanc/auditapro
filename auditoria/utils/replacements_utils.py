import os
import json
import logging
from django.conf import settings
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def _load_json_config(file_name: str) -> dict:
    """
    Función auxiliar para cargar archivos JSON de configuración
    """
    try:
        json_path = os.path.join(settings.BASE_DIR, 'auditoria', 'config', file_name)
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error al leer el archivo {file_name}: {str(e)}")
        return {}

def get_replacements_config() -> dict:
    """
    Lee la configuración de reemplazos
    """
    return _load_json_config('replacements.json')

def get_tables_config() -> dict:
    """
    Lee la configuración de tablas
    """
    return _load_json_config('tables.json')

def _format_value(value: float) -> str:
    """
    Formatea valores numéricos de manera consistente
    """
    return f"{float(value):,.2f}"

def build_replacements_dict(
    config: dict,
    audit: Any,
    fecha_inicio: str,
    fecha_fin: str,
) -> dict:
    """
    Construye el diccionario de reemplazos básicos (sin procesamiento de balance)
    """
    replacements = {}

    # Procesar entidad
    if 'entidad' in config:
        entidad_valor = audit.identidad or config['entidad']['default']
        for placeholder in config['entidad']['placeholders']:
            replacements[placeholder] = entidad_valor

        if 'formatos' in config['entidad']:
            for formato in config['entidad']['formatos'].values():
                template = formato.get('template', '{}')
                for placeholder in formato.get('placeholders', []):
                    replacements[placeholder] = template.format(entidad_valor)
        replacements['[ENTIDAD_COMPLETA]'] = f"Entidad: {entidad_valor}"
        # NUEVO: reemplazo literal de encabezado
        replacements['Entidad: '] = f"Entidad: {entidad_valor}"

    # Procesar fechas
    if 'fecha_rango' in config:
        fecha_rango = f"Del {fecha_inicio} al {fecha_fin}"
        replacements.update({
            placeholder: fecha_rango
            for placeholder in config['fecha_rango']['placeholders']
        })
        replacements.update({
            '[FECHA_INICIO]': fecha_inicio,
            '[FECHA_FIN]': fecha_fin,
            '[FECHA_RANGO_COMPLETA]': f"Período: {fecha_rango}"
        })
        # NUEVO: reemplazo literal de encabezado
        replacements['Período: '] = f"Período: {fecha_rango}"

    # Procesar título y tipo de auditoría
    if 'titulo_auditoria' in config:
        titulo = audit.title or config['titulo_auditoria']['default']
        replacements[config['titulo_auditoria']['placeholder']] = titulo
        replacements['[AUDITORIA_COMPLETA]'] = f"Auditoría: {titulo}"
        # NUEVO: mapear frases literales a título
        for literal in config['titulo_auditoria'].get('placeholders', []):
            replacements[literal] = titulo
        # NUEVO: reemplazo literal de encabezado
        replacements['Auditoría: '] = f"Auditoría: {titulo}"

    if 'tipo_auditoria' in config:
        tipo = config['tipo_auditoria']['values'].get(
            audit.tipoAuditoria,
            config['tipo_auditoria']['values']['F']
        )
        replacements[config['tipo_auditoria']['placeholder']] = tipo

    # Procesar auditor
    if 'auditor' in config:
        auditor = (audit.audit_manager.get_full_name() 
                  if audit.audit_manager 
                  else config['auditor']['default'])
        replacements[config['auditor']['placeholder']] = auditor

    # Procesar moneda
    if 'moneda' in config:
        moneda_codigo = getattr(audit, 'moneda', 'GTQ')  # Obtener código de moneda de la auditoría
        moneda_config = config['moneda']
        
        # Obtener el nombre de la moneda en español
        moneda_nombre = moneda_config['currency_names'].get(
            moneda_codigo, 
            moneda_config['default']
        )
        
        # Crear el texto de reemplazo usando el template
        moneda_texto = moneda_config['template'].format(moneda_nombre)
        
        # Aplicar a todos los placeholders
        for placeholder in moneda_config['placeholders']:
            replacements[placeholder] = moneda_texto

    # Nota: El procesamiento de balance ha sido eliminado
    logger.debug(f"Total de reemplazos generados: {len(replacements)}")
    if replacements:
        sample_keys = list(replacements.keys())[:3]
        logger.debug(f"Ejemplos de reemplazos: {sample_keys}")
        for key in sample_keys:
            logger.debug(f"  {key}: {replacements[key]}")

    return replacements
