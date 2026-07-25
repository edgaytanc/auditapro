# Mapeo de prefijos a carpetas para auditoría interna (árbol de plantillas 2026).
#
# El árbol nuevo de Auditoría Interna aplana el antiguo
# "6 AUDITORIA DE PROCESOS/<área>/5 PRUEBAS*" en una sola carpeta
# "4 PRUEBAS DE PROCESO" con 11 papeles de trabajo. Cada letra histórica se
# asocia al papel temáticamente equivalente para que los enlaces de patrón
# existentes sigan resolviendo a un archivo real.
INTERNAL_PREFIX_TO_FOLDER = {
    'B': '4 PRUEBAS DE PROCESO',   # (antes: inventarios y almacenes)
    'D': '4 PRUEBAS DE PROCESO',   # (antes: comercial / ventas)
    'E': '4 PRUEBAS DE PROCESO',   # (antes: tesorería)
    'F': '4 PRUEBAS DE PROCESO',   # (antes: contabilidad)
    'H': '4 PRUEBAS DE PROCESO',   # (antes: compras)
    'K': '4 PRUEBAS DE PROCESO',   # (antes: recursos humanos)
    'L': '4 PRUEBAS DE PROCESO',   # (antes: tecnología)
    'M': '4 PRUEBAS DE PROCESO',   # (antes: legal)
    'N': '4 PRUEBAS DE PROCESO',   # (antes: servicios públicos)
    'O': '4 PRUEBAS DE PROCESO',   # (antes: obras públicas)
    'P': '4 PRUEBAS DE PROCESO',   # (antes: gestión de ahorro)
    'Q': '4 PRUEBAS DE PROCESO',   # (antes: gestión de créditos)
}

# Papel equivalente por área histórica dentro de "4 PRUEBAS DE PROCESO".
_EQUIVALENTES = {
    'B': '6_Pruebas_en_Cierre_Contable.xlsx',
    'D': '4_Pruebas_en_Ventas.xlsx',
    'E': '3_Pruebas_en_Tesoreria_y_Flujo_de_Efectivo.xlsx',
    'F': '6_Pruebas_en_Cierre_Contable.xlsx',
    'H': '1_Pruebas_en_Compras.xlsx',
    'K': '8_Pruebas_en_Recursos_Humanos_y_Nomina.xlsx',
    'L': '9_Pruebas_en_Tecnologia_de_Informacion.xlsx',
    'M': '10_Cumplimiento_Normativo.xlsx',
    'N': '10_Cumplimiento_Normativo.xlsx',
    'O': '10_Cumplimiento_Normativo.xlsx',
    'P': '11_Prueba_Ahorro_y_Credito.xlsx',
    'Q': '11_Prueba_Ahorro_y_Credito.xlsx',
}

# Los patrones históricos (X-n) de cada área apuntan ahora al papel
# equivalente del área. Rango conservador 1..12 (max_range histórico).
INTERNAL_PATTERN_TO_FILE = {
    f"{letter}-{n}": archivo
    for letter, archivo in _EQUIVALENTES.items()
    for n in range(1, 13)
}

# Programas por área: el árbol nuevo no incluye programas .docx por proceso;
# se conserva el diccionario vacío por compatibilidad de importación.
INTERNAL_PREFIX_TO_PROGRAM = {}
