import re

def obtener_fecha_ultimo_dia_año_reciente(balances):
    """Obtiene la fecha del último día del año más reciente de los balances"""
    patron_fecha = re.compile(r'ANUAL-(\d{4}-\d{2}-\d{2})')
    fechas = {}
    
    for clave in balances:
        if match := patron_fecha.search(clave):
            fecha_completa = match.group(1)
            año = fecha_completa.split('-')[0]
            
            if fecha_completa.endswith('12-31'):
                if año not in fechas or fecha_completa > fechas[año]:
                    fechas[año] = fecha_completa
    
    if not fechas:
        return None, None
    
    año_mas_reciente = max(fechas.keys())
    return fechas[año_mas_reciente], año_mas_reciente

def extraer_cuentas_balance_ultimo_dia(balances, fecha_ultimo_dia):
    """Extrae todas las cuentas de todas las secciones del último día del año más reciente"""
    cuentas_por_seccion = {seccion: {} for seccion in ['Activo', 'Pasivo', 'Patrimonio', 'ESTADO DE RESULTADOS']}
    patron_clave = re.compile(f'ANUAL-{fecha_ultimo_dia}-(.*?)-(.*)')
    
    for clave, valor in balances.items():
        if match := patron_clave.match(clave):
            seccion, cuenta = match.groups()
            if seccion in cuentas_por_seccion:
                cuentas_por_seccion[seccion][cuenta] = valor
    
    return cuentas_por_seccion

def extraer_cuentas_saldos_iniciales(saldos_iniciales):
    """Extrae todas las cuentas de los saldos iniciales"""
    cuentas = {}
    todas_las_fechas = set()
    
    for clave, valor in saldos_iniciales.items():
        partes = clave.split('-')
        if len(partes) >= 2:
            cuenta = partes[0]
            fecha = '-'.join(partes[1:])
            
            if cuenta not in cuentas:
                cuentas[cuenta] = {}
            
            cuentas[cuenta][fecha] = valor
            todas_las_fechas.add(fecha)
    
    # Seleccionar el valor más reciente para cada cuenta
    cuentas_con_valor_mas_reciente = {
        cuenta: max(fechas_valores.items(), key=lambda x: x[0])[1]
        for cuenta, fechas_valores in cuentas.items() if fechas_valores
    }
    
    fecha_mas_reciente = max(todas_las_fechas) if todas_las_fechas else None
    return cuentas_con_valor_mas_reciente, fecha_mas_reciente
