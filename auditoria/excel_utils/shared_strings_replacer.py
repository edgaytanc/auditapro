"""
Reemplazador de texto en archivos XLSM usando manipulación directa de XML.
Funciona como fallback cuando xlwings no está disponible.
"""

import zipfile

def replace_in_xlsm_shared_strings(src_path: str, dst_path: str, replacements: dict):
    """
    Copia un .xlsm y reemplaza placeholders en:
    - xl/sharedStrings.xml
    - xl/worksheets/*.xml (inlineStr y headerFooter)
    - xl/drawings/*.xml (textos en shapes)
    Devuelve una copia con reemplazos sin tocar macros.
    
    Args:
        src_path: Ruta del archivo XLSM origen
        dst_path: Ruta del archivo XLSM destino
        replacements: Diccionario con los reemplazos a aplicar
        
    Returns:
        None (modifica el archivo destino)
    """
    total_hits = 0
    files_touched = []
    
    with zipfile.ZipFile(src_path, 'r') as zin, zipfile.ZipFile(dst_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            
            # Determinar si el archivo necesita procesamiento de texto
            needs_text_replace = (
                item.filename == 'xl/sharedStrings.xml' or
                (item.filename.startswith('xl/worksheets/') and item.filename.endswith('.xml')) or
                (item.filename.startswith('xl/drawings/') and item.filename.endswith('.xml'))
            )
            
            if needs_text_replace:
                try:
                    text = data.decode('utf-8')
                except UnicodeDecodeError:
                    text = data.decode('utf-8', errors='ignore')
                
                file_hits = 0
                for k, v in replacements.items():
                    if not isinstance(v, str):
                        v = str(v)
                    if not k:
                        continue
                    
                    occurrences = text.count(k)
                    if occurrences:
                        text = text.replace(k, v)
                        file_hits += occurrences
                
                if file_hits:
                    files_touched.append((item.filename, file_hits))
                    total_hits += file_hits
                
                data = text.encode('utf-8')
            
            zout.writestr(item, data)

def build_filtered_replacements(replacements_all: dict) -> dict:
    """
    Filtra los reemplazos para incluir solo las llaves permitidas en XLSM.
    
    Args:
        replacements_all: Diccionario completo de reemplazos
        
    Returns:
        dict: Diccionario filtrado con reemplazos permitidos
    """
    def _allow(k: str) -> bool:
        if not isinstance(k, str):
            return False
        if k.startswith('[') and k.endswith(']'):
            return True
        prefixes = (
            'Entidad', 'Auditoría', 'Auditoria', 'Período', 'Periodo'
        )
        return any(k.startswith(p) for p in prefixes)
    
    filtered_repl = {k: v for k, v in replacements_all.items() if _allow(k)}
    
    # Forzar reemplazo de etiquetas "Período:"/"Periodo:" sin placeholder
    period_value = None
    for key in ('[FECHA_RANGO_COMPLETA]', '[FECHA_RANGO]'):
        if key in replacements_all and isinstance(replacements_all[key], (str, int, float)):
            period_value = str(replacements_all[key])
            break
    
    if period_value:
        # Variantes comunes con y sin espacio adicional
        for label in ('Período:', 'Periodo:', 'Período :', 'Periodo :'):
            filtered_repl[label] = f"{label.split(':')[0]}: {period_value}"
        
        # Reemplazo del literal fijo del template
        default_period_literals = [
            'Del 01 de Enero al 31 de Diciembre de 2024',
            'DEL 01 DE ENERO AL 31 DE DICIEMBRE DE 2024',
            'Del 01 de enero al 31 de diciembre de 2024',
        ]
        period_only = period_value.replace('Período:', '').replace('Periodo:', '').strip()
        for lit in default_period_literals:
            filtered_repl[lit] = period_only
    
    return filtered_repl
