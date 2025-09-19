import re

def normalizar_balances(balances):
    """
    Normaliza las claves del diccionario balances eliminando los sufijos de tipo_cuenta.

    Args:
        balances: Diccionario original de balances

    Returns:
        Diccionario con claves normalizadas (sin sufijos de tipo_cuenta)
    """
    balances_normalizados = {}
    # Acepta C, NC, NT, Corriente y No Corriente (con espacio o guion), case-insensitive
    patron_sufijo = re.compile(r'^(.*?)-(?:C|NC|NT|CORRIENTE|NO[ -]?CORRIENTE)$', re.IGNORECASE)

    for clave, valor in balances.items():
        # Verificar si la clave tiene un sufijo de tipo_cuenta
        match = patron_sufijo.match(clave)
        if match:
            # Extraer la parte principal de la clave sin el sufijo
            clave_base = match.group(1).strip()
            balances_normalizados[clave_base] = valor
        else:
            balances_normalizados[clave] = valor

    return balances_normalizados