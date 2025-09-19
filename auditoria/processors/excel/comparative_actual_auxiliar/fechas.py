from datetime import datetime

def obtener_año_mas_reciente(balances):
    """Obtiene el año más reciente de los balances y devuelve la clave base 'TIPO-YYYY-MM-DD'.
    
    Ejemplo de retorno: 'ANUAL-2024-12-31' o 'SEMESTRAL-2024-06-30'
    """
    años = {}

    for clave in balances.keys():
        partes = clave.split('-')
        if len(partes) >= 4:
            tipo, fecha = partes[0], f"{partes[1]}-{partes[2]}-{partes[3]}"
            try:
                fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
                año = fecha_obj.year
                if año not in años or fecha_obj > años[año]['fecha']:
                    años[año] = {'fecha': fecha_obj, 'tipo': tipo, 'fecha_str': fecha}
            except ValueError:
                continue

    if not años:
        return None

    año_mas_reciente = max(años.keys())
    data = años[año_mas_reciente]
    return f"{data['tipo']}-{data['fecha_str']}"
