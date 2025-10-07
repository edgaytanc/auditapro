def extraer_fechas_anuales(balances):
    """Extrae las fechas anuales únicas del diccionario balances y las devuelve ordenadas."""
    fechas = set()
    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 4 and partes[0] == 'ANUAL':
            fecha = f"{partes[1]}-{partes[2]}-{partes[3]}"
            fechas.add(fecha)
    return sorted(list(fechas))

def clasificar_cuentas_por_seccion_y_tipo(balances, año_actual, año_anterior):
    """
    Clasifica las cuentas por sección y tipo, organizadas por año.
    """
    estructura = {
        'Activo': {
            'Corriente': {año_actual: {}, año_anterior: {}},
            'No Corriente': {año_actual: {}, año_anterior: {}}
        },
        'Pasivo': {
            'Corriente': {año_actual: {}, año_anterior: {}},
            'No Corriente': {año_actual: {}, año_anterior: {}}
        },
        'Patrimonio': {año_actual: {}, año_anterior: {}},
        'ESTADO DE RESULTADOS': {año_actual: {}, año_anterior: {}}
    }

    for clave, valor in balances.items():
        partes = clave.split('-')
        if len(partes) >= 6 and partes[0] == 'ANUAL':
            fecha = f"{partes[1]}-{partes[2]}-{partes[3]}"
            if fecha not in [año_actual, año_anterior]:
                continue

            seccion = partes[4]
            cuenta = partes[5]
            tipo_cuenta = partes[6]

            if seccion in estructura:
                if seccion in ['Activo', 'Pasivo'] and tipo_cuenta in estructura[seccion]:
                    estructura[seccion][tipo_cuenta][fecha][cuenta] = valor
                elif seccion in ['Patrimonio', 'ESTADO DE RESULTADOS']:
                    estructura[seccion][fecha][cuenta] = valor

    return estructura
