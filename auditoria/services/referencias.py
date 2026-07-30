"""
Servicio de referencias automáticas de papeles de trabajo (guía de módulos 2026).

Cada papel de trabajo recibe un código de Referencia (Ref.) según su posición
en el árbol de carpetas del tipo de auditoría:

- Archivos de "4 PRUEBAS SUSTANTIVAS/<área>" (financiera): sistema de LETRAS
  ya existente (A..J, R). El programa del área se muestra como 'X' y los demás
  papeles como 'X-n', exactamente igual que PATTERN_TO_FILE / SPECIAL_PATTERNS
  (única fuente de verdad: se importan e invierten esos diccionarios).
- Resto del árbol: códigos jerárquicos por posición (1-based) según el JSON de
  estructura: carpeta i -> 'i', subcarpeta j -> 'i.j', archivo k -> 'i.j.k'.
"""

import json
import os
import re
import unicodedata
from functools import lru_cache

from django.conf import settings

from auditoria.processors.shared.urls_programs.financial_audit_mappings import (
    PREFIX_TO_FOLDER,
    PATTERN_TO_FILE,
)
from auditoria.processors.shared.urls_programs.special_patterns import (
    PREFIX_TO_PROGRAM,
)

# Archivos JSON de estructura por tipo de auditoría
_JSON_POR_TIPO = {
    'F': 'folder_structure_financiera.json',
    'I': 'folder_structure_interna.json',
    'R': 'folder_structure_revisoria.json',
}

# Letras de sumarias referenciadas por cada centralizadora (por palabra clave
# del nombre de archivo, en orden de comprobación).
_CENTRALIZADORA_LETRAS = [
    ('ESTADO', ['R']),
    ('ACTIVO', ['A', 'B', 'C', 'D', 'E', 'F', 'G']),
    ('PASIVO', ['H', 'I', 'J']),
    ('BALANCE', ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']),
]

# Reglas (ordenadas, gana la primera coincidencia) de palabra clave -> letra
# de área sustantiva. Alineadas con _MAPEO_CUENTAS de sumaria/deteccion.py.
_REGLAS_CUENTA_LETRA = [
    (('PASIVO LARGO PLAZO', 'PRESTAMO', 'FINANCIAMIENTO'), 'I'),
    (('RESULTADOS DE EJERCICIOS', 'RESULTADO DE EJERCICIOS', 'EJERCICIOS ANTERIORES'), 'J'),
    (('EFECTIVO', 'CAJA', 'BANCO'), 'A'),
    (('COBRAR', 'CLIENTE'), 'B'),
    (('INVERSION',), 'C'),
    (('INVENTARIO',), 'D'),
    (('CONSTRUCCION',), 'E'),
    (('PROPIEDAD', 'PLANTA', 'EQUIPO', 'ACTIVO FIJO'), 'F'),
    (('INTANGIBLE',), 'G'),
    (('PAGAR', 'PROVEEDOR'), 'H'),
    (('PATRIMONIO', 'CAPITAL', 'RESERVA'), 'J'),
    (('INGRESO', 'COSTO', 'GASTO', 'EGRESO', 'RESULTADO', 'IMPUESTO', 'UTILIDAD'), 'R'),
]


def _normalizar_texto(texto):
    """Normaliza texto: sin tildes, minúsculas y espacios colapsados."""
    s = unicodedata.normalize('NFD', str(texto))
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.lower().split())


def _clave_normalizada(carpeta, archivo):
    """Clave de búsqueda tolerante a tildes y separadores de ruta."""
    carpeta = (carpeta or '').replace('\\', '/').strip('/')
    return (_normalizar_texto(carpeta), _normalizar_texto(archivo))


def _indice_letras_financiera():
    """Invierte los mapeos de patrones: (carpeta, archivo) -> ref de letra."""
    indice = {}
    # Programas de área: se muestran solo con la letra ('A', 'B', ...)
    for prefijo, carpeta in PREFIX_TO_FOLDER.items():
        programa = PREFIX_TO_PROGRAM.get(prefijo)
        if programa:
            indice[(carpeta, programa)] = prefijo
    # Papeles 'X-n'
    for patron, archivo in PATTERN_TO_FILE.items():
        prefijo = patron.split('-')[0]
        carpeta = PREFIX_TO_FOLDER.get(prefijo)
        if carpeta:
            indice.setdefault((carpeta, archivo), patron)
    return indice


def _cargar_estructura(tipo_auditoria):
    nombre_json = _JSON_POR_TIPO.get(tipo_auditoria, _JSON_POR_TIPO['F'])
    json_path = os.path.join(settings.BASE_DIR, 'auditoria', 'config', nombre_json)
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


@lru_cache(maxsize=8)
def construir_indice(tipo_auditoria):
    """
    Construye el índice de referencias para un tipo de auditoría.

    Returns:
        dict: (carpeta_relativa, nombre_archivo) -> código de referencia.
              La carpeta usa separador '/' tal como aparece en el JSON.
    """
    estructura = _cargar_estructura(tipo_auditoria)
    letras = _indice_letras_financiera() if tipo_auditoria == 'F' else {}
    indice = {}

    def recorrer(nodo, carpeta_actual, codigo_padre):
        posicion = 0
        for nombre, contenido in nodo.items():
            posicion += 1
            codigo = f"{codigo_padre}.{posicion}" if codigo_padre else str(posicion)
            if isinstance(contenido, dict):
                nueva_carpeta = f"{carpeta_actual}/{nombre}" if carpeta_actual else nombre
                recorrer(contenido, nueva_carpeta, codigo)
            else:
                clave = (carpeta_actual, nombre)
                # El sistema de letras tiene prioridad sobre el código posicional
                indice[clave] = letras.get(clave, codigo)

    recorrer(estructura, '', '')
    return indice


@lru_cache(maxsize=8)
def _indice_normalizado(tipo_auditoria):
    """Variante del índice con claves normalizadas (tildes/separadores)."""
    return {
        _clave_normalizada(carpeta, archivo): ref
        for (carpeta, archivo), ref in construir_indice(tipo_auditoria).items()
    }


def limpiar_cache():
    """Limpia los índices cacheados (p. ej. tras editar los JSON de estructura)."""
    construir_indice.cache_clear()
    _indice_normalizado.cache_clear()


def ref_automatica(tipo_auditoria, carpeta, archivo):
    """Referencia que calcula el sistema, sin considerar la del auditor."""
    if not tipo_auditoria or not archivo:
        return None
    indice = construir_indice(tipo_auditoria)
    carpeta_limpia = (carpeta or '').replace('\\', '/').strip('/')
    ref = indice.get((carpeta_limpia, archivo))
    if ref:
        return ref
    return _indice_normalizado(tipo_auditoria).get(_clave_normalizada(carpeta, archivo))


def ref_manual(audit_id, carpeta, archivo):
    """
    Referencia fijada a mano por el auditor para ese papel, o None.

    Se busca primero por coincidencia exacta y luego normalizando tildes y
    separadores, porque la carpeta llega desde la URL y desde el árbol con
    formatos ligeramente distintos.
    """
    if not audit_id or not archivo:
        return None

    from auditoria.models import ReferenciaPapelTrabajo

    carpeta_limpia = (carpeta or '').replace('\\', '/').strip('/')
    registros = ReferenciaPapelTrabajo.objects.filter(audit_id=audit_id)

    exacto = registros.filter(carpeta=carpeta_limpia, archivo=archivo).first()
    if exacto:
        return exacto.referencia

    buscado = _clave_normalizada(carpeta_limpia, archivo)
    for registro in registros:
        if _clave_normalizada(registro.carpeta, registro.archivo) == buscado:
            return registro.referencia
    return None


def obtener_ref(tipo_auditoria, carpeta, archivo, audit_id=None):
    """
    Devuelve la referencia de un papel de trabajo o None si no se conoce.

    Si el auditor fijó una referencia propia para ese papel en esta auditoría,
    ESA manda: el sistema no la sobrescribe (respuesta a la consulta del
    cliente sobre si puede mantener sus propias letras/números).

    Args:
        tipo_auditoria: 'F', 'I' o 'R'
        carpeta: ruta relativa de la carpeta (separador '/' o '\\')
        archivo: nombre del archivo
        audit_id: auditoría en curso, para consultar la referencia manual
    """
    manual = ref_manual(audit_id, carpeta, archivo)
    if manual:
        return manual
    return ref_automatica(tipo_auditoria, carpeta, archivo)


def _archivo_de_ref(ref, tipo_auditoria):
    """Busca (carpeta, archivo) a partir de una referencia ya asignada."""
    for clave, codigo in construir_indice(tipo_auditoria).items():
        if codigo == ref:
            return clave
    return None


def vinculos_de(ref, tipo_auditoria='F'):
    """
    Devuelve las etiquetas de los papeles vinculados automáticamente a *ref*.

    - Sumaria 'X-1'      -> programa del área y centralizadora.
    - Programa 'X'       -> sus papeles 'X-n' (máximo 8).
    - Centralizadoras    -> las sumarias de las áreas que consolidan.
    - Otro papel 'X-n'   -> programa y sumaria del área.
    Lista vacía cuando no hay vínculos conocidos.
    """
    if not ref or tipo_auditoria != 'F':
        return []
    ref = ref.strip()

    # Programa de área ('A' o 'A-programa')
    prefijo = ref.split('-')[0]
    if ref in PREFIX_TO_FOLDER or ref.endswith('-programa'):
        hijos = sorted(
            (p for p in PATTERN_TO_FILE if p.split('-')[0] == prefijo),
            key=lambda p: int(p.split('-')[1]),
        )
        return hijos[:8]

    # Papeles del sistema de letras
    if re.fullmatch(r'[A-JR]-\d+', ref) and prefijo in PREFIX_TO_FOLDER:
        if ref.endswith('-1'):
            # Cédula sumaria del área
            return [f"{prefijo} (programa)", "CENTRALIZADORA correspondiente"]
        return [f"{prefijo} (programa)", f"{prefijo}-1 (sumaria)"]

    # Centralizadoras (código jerárquico): vinculan a las sumarias que consolidan
    encontrado = _archivo_de_ref(ref, tipo_auditoria)
    if encontrado:
        _, archivo = encontrado
        nombre = _normalizar_texto(archivo).upper()
        if 'CENTRALIZADORA' in nombre:
            for palabra, letras in _CENTRALIZADORA_LETRAS:
                if palabra in nombre:
                    return [f"{letra}-1 (sumaria)" for letra in letras]

    return []


def ref_para_cuenta(nombre_cuenta, seccion=None):
    """
    Devuelve la referencia de la cédula sumaria ('A-1', 'H-1', ...) asociada a
    una cuenta del balance, por palabras clave. None si no se reconoce.

    La *seccion* de origen (cuando se conoce) manda sobre las palabras clave
    en los casos ambiguos: una cuenta de la sección Patrimonio siempre
    referencia J-1 (p. ej. 'Resultado del ejercicio'), y una del Estado de
    Resultados siempre R-1.
    """
    if not nombre_cuenta:
        return None
    if seccion:
        seccion_norm = _normalizar_texto(str(seccion)).upper()
        if "PATRIMONIO" in seccion_norm:
            return "J-1"
        if "RESULTADO" in seccion_norm:  # 'ESTADO DE RESULTADOS'
            return "R-1"
    texto = _normalizar_texto(nombre_cuenta).upper()
    for palabras, letra in _REGLAS_CUENTA_LETRA:
        if any(palabra in texto for palabra in palabras):
            return f"{letra}-1"
    return None


def _celda_destino_derecha(sheet, cell):
    """
    Celda editable a la derecha de *cell*, saltando el rango combinado al que
    pertenezca la etiqueta. None si la celda resultante no es editable.
    """
    from openpyxl.cell.cell import MergedCell

    columna = cell.column + 1
    for rango in sheet.merged_cells.ranges:
        if rango.min_row <= cell.row <= rango.max_row and rango.min_col <= cell.column <= rango.max_col:
            columna = rango.max_col + 1
            break
    destino = sheet.cell(row=cell.row, column=columna)
    if isinstance(destino, MergedCell):
        return None
    return destino


# Hueco de la referencia dentro de la propia etiqueta: 'Ref.      XXXXXX'
_PATRON_HUECO_REF = re.compile(r'(x{3,})', re.IGNORECASE)

# Un recuadro cuyo contenido completo es un código de referencia: 'PL-1.1',
# 'B-4', 'INF-05', 'A-1', 'CC-BG'...  (las plantillas Word lo traen así)
_PATRON_TOKEN_REF = re.compile(
    r'^(?:PL|INF|PRA|CC|ER|[A-JR])-?\d+(?:[.\-]\d+)*$', re.IGNORECASE)

# Recuadro que solo trae la etiqueta, sin valor: 'Ref.' / 'Ref'
# (deliberadamente NO coincide con encabezados de columna como 'REF. PT')
_PATRON_SOLO_ETIQUETA_REF = re.compile(r'^ref\.?$', re.IGNORECASE)


def inyectar_ref_propia(workbook, ref):
    """
    Escribe la referencia propia del papel en el recuadro 'Ref.' del encabezado
    (filas 1-12, columnas 1-15) de cada hoja.

    Las plantillas oficiales resuelven ese recuadro de dos maneras:
      · 'Ref.' en una celda y el hueco en la de al lado, o
      · 'Ref.      XXXXXX' todo en la misma celda.
    Se cubren las dos. Nunca se pisa un valor que el auditor ya haya escrito.
    """
    if not ref:
        return workbook

    for sheet in workbook.worksheets:
        max_row = min(sheet.max_row or 1, 12)
        max_col = min(sheet.max_column or 1, 15)
        procesada = False
        for row in sheet.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_col):
            for cell in row:
                if not isinstance(cell.value, str):
                    continue
                if not _normalizar_texto(cell.value).startswith('ref'):
                    continue

                # Caso 'Ref.      XXXXXX': se rellena el hueco en la misma celda
                if _PATRON_HUECO_REF.search(cell.value):
                    cell.value = _PATRON_HUECO_REF.sub(ref, cell.value, count=1)
                    procesada = True
                    break

                destino = _celda_destino_derecha(sheet, cell)
                if destino is not None and destino.value in (None, ''):
                    destino.value = ref
                procesada = True
                break
            if procesada:
                break
    return workbook


# ---------------------------------------------------------------------------
# Referencia propia en plantillas Word
# ---------------------------------------------------------------------------

def _textos_de(nodo):
    """Elementos <w:t> contenidos en *nodo*, en orden de lectura."""
    from docx.oxml.ns import qn
    return nodo.findall('.//' + qn('w:t'))


def _texto_unido(elementos):
    """Texto completo de un grupo de <w:t> (Word parte las palabras en runs)."""
    return ''.join(elemento.text or '' for elemento in elementos)


def _escribir_en_grupo(elementos, valor):
    """Escribe *valor* en el primer <w:t> y vacía los demás del grupo."""
    elementos[0].text = valor
    for elemento in elementos[1:]:
        elemento.text = ''


def _valor_ref_para_grupo(elementos, ref):
    """
    Decide qué texto debe quedar en un grupo de <w:t> (un recuadro, una celda o
    un párrafo) para que muestre la referencia, o None si ese grupo no es el
    hueco de la referencia.

    Word reparte el texto entre varios runs ('PL-1' + '.2'), así que se evalúa
    el contenido unido.
    """
    if not elementos:
        return None
    unido = _texto_unido(elementos)
    if not unido.strip():
        return None

    # Los recuadros de logo comparten forma con los de referencia: no se tocan
    if 'LOGO' in unido.upper():
        return None

    plano = unido.strip()
    compacto = re.sub(r'\s+', '', plano)

    # 1) Hueco explícito DETRÁS de la etiqueta: 'Ref.   XXXXXX'.
    #    Se exige la etiqueta porque en estas plantillas un 'XXXX' suelto es el
    #    hueco de OTRO dato (nombre de la entidad, 'UDAI No. [XXXX-XXXX]'...) y
    #    no debe secuestrarlo la referencia.
    if (_normalizar_texto(plano).startswith('ref')
            and _PATRON_HUECO_REF.search(plano)):
        return _PATRON_HUECO_REF.sub(ref, plano, count=1)

    # 2) El recuadro ya trae un código de referencia de la plantilla: se sustituye
    if _PATRON_TOKEN_REF.match(compacto):
        return ref

    # 3) Solo la etiqueta, sin valor ('Ref.')
    if _PATRON_SOLO_ETIQUETA_REF.match(compacto):
        return f"Ref. {ref}"

    return None


def _firma_grupo(elementos):
    """Identidad del contenido de un grupo, para detectar copias del recuadro."""
    return re.sub(r'\s+', '', _texto_unido(elementos)).upper()


def _partes_con_encabezados(documento):
    """Documento + sus encabezados y pies, donde también vive el recuadro."""
    partes = [documento.element.body]
    for seccion in documento.sections:
        for contenedor in (seccion.header, seccion.first_page_header,
                           seccion.even_page_header, seccion.footer,
                           seccion.first_page_footer, seccion.even_page_footer):
            try:
                if contenedor is not None:
                    partes.append(contenedor._element)
            except Exception:
                # Alguna variante de encabezado puede no existir en la plantilla
                continue
    return partes


def _grupos_candidatos(partes, limite_parrafos=25):
    """
    Grupos de <w:t> donde puede vivir la referencia, en orden de prioridad:
    primero los cuadros de texto (el caso habitual) y después los párrafos del
    inicio del cuerpo y de los encabezados.
    """
    from docx.oxml.ns import qn

    cuadros, parrafos = [], []
    for parte in partes:
        for cuadro in parte.findall('.//' + qn('w:txbxContent')):
            cuadros.append(_textos_de(cuadro))
        # Los párrafos que ya están dentro de un cuadro no se repiten aquí
        dentro_de_cuadro = {
            id(elemento)
            for cuadro in parte.findall('.//' + qn('w:txbxContent'))
            for elemento in cuadro.findall('.//' + qn('w:p'))
        }
        contador = 0
        for parrafo in parte.findall('.//' + qn('w:p')):
            if id(parrafo) in dentro_de_cuadro:
                continue
            if contador >= limite_parrafos:
                break
            contador += 1
            parrafos.append(_textos_de(parrafo))
    return cuadros + parrafos


def _agregar_recuadro_ref(documento, ref):
    """
    Añade la referencia arriba a la derecha cuando la plantilla no trae recuadro.

    Así ningún papel de trabajo en Word queda sin su Ref., igual que en Excel.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    if documento.paragraphs:
        parrafo = documento.paragraphs[0].insert_paragraph_before()
    else:
        parrafo = documento.add_paragraph()
    ejecucion = parrafo.add_run(f"Ref. {ref}")
    ejecucion.bold = True
    parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    return documento


def inyectar_ref_propia_word(documento, ref):
    """
    Escribe la referencia propia del papel en la plantilla Word.

    Las plantillas oficiales resuelven el recuadro 'Ref.' de varias formas y
    ninguna es alcanzable con la API de párrafos de python-docx:

      · cuadro de texto (w:txbxContent) en el cuerpo — el caso más común,
        con el código de la plantilla dentro ('PL-1.1', 'INF-2', 'B-4');
      · cuadro de texto o texto suelto en el encabezado de página;
      · hueco 'XXXXXX' o etiqueta 'Ref.' sin valor.

    Se cubren todas y, si la plantilla no trae recuadro, se agrega la
    referencia arriba a la derecha. Nunca se pisan los recuadros de logo ni
    los encabezados de columna tipo 'REF. PT'.

    Word guarda cada forma DOS veces (mc:Choice moderno y mc:Fallback heredado),
    así que el recuadro se rellena en TODAS sus copias: si solo se escribiera la
    primera, Word podía seguir mostrando el código viejo de la plantilla.
    """
    if not ref:
        return documento

    grupos = _grupos_candidatos(_partes_con_encabezados(documento))

    # Primer grupo que sea el hueco de la referencia
    objetivo = None
    for elementos in grupos:
        valor = _valor_ref_para_grupo(elementos, ref)
        if valor is not None:
            objetivo = (_firma_grupo(elementos), valor)
            break

    if objetivo is None:
        # La plantilla no trae recuadro: se agrega arriba a la derecha
        return _agregar_recuadro_ref(documento, ref)

    firma_objetivo, valor = objetivo
    for elementos in grupos:
        if _firma_grupo(elementos) == firma_objetivo:
            _escribir_en_grupo(elementos, valor)
    return documento
