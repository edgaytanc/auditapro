"""
Identificador único de un papel de trabajo.

El informe del cliente apuntaba a «una falla en la capa de mapeo entre el
identificador de cada plantilla y el que usa el motor de importación». Había
tres copias de la normalización —`AuditMarkProcessor.normalize_text`,
`WorkPaperValidator.normalize_text` y `TemplateFile._normalize_name`— que
podían divergir. Aquí vive la única, y las tres delegan en ella.

Reglas, en orden:

  1. Se quita el número consecutivo del principio ('2 ', '4.1 ', '10_').
  2. Se quita la extensión.
  3. Se quitan las tildes y todo lo que no sea letra o número.
  4. Se quitan los conectores ('Y', 'DE', 'DEL', 'LA'…): el auditor escribe
     «CUESTIONARIO CAJA Y BANCOS» y el archivo se llama
     «1_Cuestionario_Caja_Bancos.xlsx»; sin esto no se reconocían como el
     mismo papel y la marca quedaba huérfana.
"""

from __future__ import annotations

import re
import unicodedata

__all__ = ['normalizar_nombre_papel', 'CONECTORES']

_NUMERO_INICIAL = re.compile(r'^\d+(?:\.\d+)*[\s_\-.]*')
_EXTENSION = re.compile(r'\.(xlsx|docx|xlsm|xls|doc|pdf)$', re.IGNORECASE)
_NO_ALFANUMERICO = re.compile(r'[^A-Z0-9]+')

# Palabras de enlace que no distinguen un papel de trabajo de otro.
CONECTORES = {
    'Y', 'E', 'O', 'U', 'DE', 'DEL', 'LA', 'LAS', 'EL', 'LOS', 'AL',
    'EN', 'PARA', 'POR', 'CON', 'A', 'SU', 'SUS', 'UN', 'UNA',
}


def normalizar_nombre_papel(texto):
    """
    Identificador comparable de un papel de trabajo.

        '2_Cedula_Sumaria_Caja_Bancos.xlsx' → 'CEDULASUMARIACAJABANCOS'
        'CUESTIONARIO CAJA Y BANCOS'        → 'CUESTIONARIOCAJABANCOS'
        '1_Cuestionario_Caja_Bancos.xlsx'   → 'CUESTIONARIOCAJABANCOS'
    """
    if not texto:
        return ''

    nombre = _EXTENSION.sub('', str(texto).strip())
    sin_numero = _NUMERO_INICIAL.sub('', nombre)
    if sin_numero.strip(' _-.'):
        nombre = sin_numero

    nombre = unicodedata.normalize('NFD', nombre)
    nombre = ''.join(c for c in nombre if unicodedata.category(c) != 'Mn')
    nombre = _NO_ALFANUMERICO.sub(' ', nombre.upper())

    palabras = nombre.split()
    if not palabras:
        return ''

    # La PRIMERA palabra nunca se descarta: los papeles se identifican con
    # letras sueltas ('A-1', 'E-2', 'O-3') que también son conectores, y
    # quitarlas convertiría 'A-1 ARQUEO' en '1ARQUEO'.
    utiles = [palabras[0]] + [p for p in palabras[1:] if p not in CONECTORES]

    return ''.join(utiles)
