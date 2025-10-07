def extraer_cuentas_por_seccion(balances_anuales, años_ordenados):
    """Extrae las cuentas de las secciones de interés (Activo, Pasivo, Patrimonio) para los dos años más recientes."""
    secciones_interes = ['Activo', 'Pasivo', 'Patrimonio']
    cuentas_por_seccion = {}

    for seccion in secciones_interes:
        cuentas_por_seccion[seccion] = {}
        for año in años_ordenados[:2]:
            cuentas_año = {}
            for key, valor in balances_anuales.items():
                if año in key and seccion in key:
                    partes = key.split(f"{seccion}-", 1)
                    if len(partes) > 1:
                        cuenta = partes[1]
                        if cuenta.strip():
                            cuentas_año[cuenta] = valor
            cuentas_por_seccion[seccion][año] = cuentas_año
            
    return cuentas_por_seccion
