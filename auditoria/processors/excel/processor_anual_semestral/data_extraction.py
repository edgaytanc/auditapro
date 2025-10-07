def extraer_y_clasificar_datos(balances):
    """Extrae fechas y clasifica cuentas de los balances para ANUAL y SEMESTRAL."""
    fechas_anual = sorted(list(set(k.split('-')[1] + '-' + k.split('-')[2] + '-' + k.split('-')[3] for k in balances if k.startswith('ANUAL-'))))
    fechas_semestral = sorted(list(set(k.split('-')[1] + '-' + k.split('-')[2] + '-' + k.split('-')[3] for k in balances if k.startswith('SEMESTRAL-'))))

    cuentas_anual = _clasificar_cuentas_por_seccion(balances, 'ANUAL')
    cuentas_semestral = _clasificar_cuentas_por_seccion(balances, 'SEMESTRAL')

    return {
        'fechas_anual': fechas_anual,
        'fechas_semestral': fechas_semestral,
        'cuentas_anual': cuentas_anual,
        'cuentas_semestral': cuentas_semestral
    }

def _clasificar_cuentas_por_seccion(balances, tipo_balance):
    """Clasifica las cuentas del balance por sección para un tipo de balance específico."""
    cuentas_por_seccion = {
        'Activo': [],
        'Pasivo': [],
        'Patrimonio': [],
        'ESTADO DE RESULTADOS': []
    }
    cuentas_vistas = set()

    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 5 and partes[0] == tipo_balance:
            seccion = partes[4]
            cuenta = '-'.join(partes[5:])
            if seccion in cuentas_por_seccion and cuenta not in cuentas_vistas:
                cuentas_por_seccion[seccion].append(cuenta)
                cuentas_vistas.add(cuenta)

    for seccion in cuentas_por_seccion:
        cuentas_por_seccion[seccion].sort()

    return cuentas_por_seccion
