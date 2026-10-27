# Mapeo de prefijos a carpetas principales
PREFIX_TO_FOLDER = {
    'A': '5 PRUEBAS SUSTANTIVAS/1 CAJA Y BANCOS',
    'B': '5 PRUEBAS SUSTANTIVAS/2 CUENTAS POR COBRAR',
    'C': '5 PRUEBAS SUSTANTIVAS/3 INVERSIONES',
    'D': '5 PRUEBAS SUSTANTIVAS/4 INVENTARIOS',
    'E': '5 PRUEBAS SUSTANTIVAS/5 CONSTRUCCIONES EN PROCESO',
    'F': '5 PRUEBAS SUSTANTIVAS/6 AUDITORIA ACTIVOS FIJOS',
    'G': '5 PRUEBAS SUSTANTIVAS/7 AUDITORIA ACTIVO INTANGIBLE',
    'H': '5 PRUEBAS SUSTANTIVAS/8 AUDITORIA CUENTAS POR PAGAR',
    'I': '5 PRUEBAS SUSTANTIVAS/9 AUDITORIA PASIVO LARGO PLAZO',
    'J': '5 PRUEBAS SUSTANTIVAS/10 AUDITORIA PATRIMONIO',
    'R': '5 PRUEBAS SUSTANTIVAS/11 AUDITORIA DE ESTADO RESULTADOS',
}

# Mapeo de patrones a nombres de archivos específicos para Caja y Bancos (A)
PATTERN_TO_FILE_A = {
    # El programa principal no tiene un patrón específico, se usa con todos los A-n
    'A-1': '2 SUMARIA CAJAS Y BANCOS.xlsx',
    'A-2': '3 CONCILIACIONES BANCARIAS.xlsx',
    'A-3': '4 CONFIRMACION BANCARIA.docx',
    'A-4': '4.1 CONTROL DE CONFIRMACIONES.xlsx',
    'A-5': '5 ARQUEO DE CAJA.xlsx',
    'A-6': '6 ARQUEOS CAJA CHICA.docx',
    'A-7': '7 CORTE DE CHEQUES.xlsx',
    'A-8': '8 INTEGRACION INGRESOS.xlsx',
    'A-9': '9 PRUEBA DE INGRESOS.xlsx',
    'A-10': '10 INTEGRACION EGRESOS.xlsx',
    'A-11': '11 PRUEBA DE EGRESOS.xlsx',
    'A-12': '12 PRUEBA DE TRANSFERENCIAS.xlsx',
    'A-13': '13 REVISION AJUSTES CONTABLES.xlsx',
    'A-14': '14 PRUEBAS CIERRE CONTABLE.xlsx',
    'A-15': '15 PARTIDAS DE AJUSTES.docx',
    'A-16': '16 PARTIDAS DE RECLASIFICACION.docx',
    'A-17': '17 HALLAZGOS.docx',
    'A-18': '18 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Cuentas por Cobrar (B)
PATTERN_TO_FILE_B = {
    'B-1': '2 SUMARIA CUENTAS POR COBRAR.xlsx',
    'B-2': '3 INTEGRACION DE CLIENTES.xlsx',
    'B-3': '4 INTEGRACION DE DEUDORES.xlsx',
    'B-4': '5 CIRCULARIZACION DE CLIENTE.docx',
    'B-5': '5 CIRCULARIZACION DE CLIENTE.docx',
    'B-6': '6 CIRCULARIZACION.docx',
    'B-7': '7 ESTADISTICA DE CIRCULARIZACION.docx',
    'B-8': '8 INSPECCIONAR.xlsx',
    'B-9': '9 ANALISIS DE ANTIGÜEDAD DE SALDOS.xlsx',
    'B-10': '10 PRUEBA DE COBROS POSTERIORES.xlsx',
    'B-11': '11 ANALISIS DE CUENTAS INCOBRABLES.xlsx',
    'B-12': '12 CORTE DE FORMAS.xlsx',
    'B-13': '13 PARTIDAS DE AJUSTES.docx',
    'B-14': '14 PARTIDAS DE RECLASIFICACION.docx',
    'B-15': '15 HALLAZGOS.docx',
    'B-16': '16 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Inversiones (C)
PATTERN_TO_FILE_C = {
    'C-1': '2 SUMARIA INVERSIONES.xlsx',
    'C-2': '3 PRUEBA FISICA INVERSIONES.xlsx',
    'C-3': '4 PARTIDAS DE AJUSTES.docx',
    'C-4': '5 PARTIDAS DE RECLASIFICACION.docx',
    'C-5': '6 HALLAZGOS.docx',
    'C-6': '7 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Inventarios (D)
PATTERN_TO_FILE_D = {
    'D-1': '2 SUMARIA INVENTARIOS.xlsx',
    'D-2': '3 INTEGRACION DE INVENTARIOS.xlsx',
    'D-3': '4 INVENTARIOS EN TRANSITO.xlsx',
    'D-4': '5 INTEGRACION INVENTARIOS OBSOLETOS.xlsx',
    'D-5': '6 ANALITICA DE INVENTARIOS.xlsx',
    'D-6': '7 MEMORANDUM TOMA FISICA DE INVENTARIO.docx',
    'D-7': '8 INVENTARIO FISICO.xlsx',
    'D-8': '9 VALUACION DE INVENTARIOS.xlsx',
    'D-9': '10 Comparar costos con precios de mercado.xlsx',
    'D-10': '11 CONFIRMACION DE INVENTARIOS.docx',
    'D-11': '12 CORTE DE FORMAS.xlsx',
    'D-12': '13 PRUEBAS DE CIERRE.docx',
    'D-13': '14 PARTIDAS DE AJUSTES.docx',
    'D-14': '15 PARTIDAS DE RECLASIFICACION.docx',
    'D-15': '16 HALLAZGOS.docx',
    'D-16': '17 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Construcciones en Proceso (E)
PATTERN_TO_FILE_E = {
    'E-1': '2 SUMARIA CONSTRUCCIONES EN PROCESO.xlsx',
    'E-2': '3 INTEGRACION DE OBRAS.xlsx',
    'E-3': '4 SOLICITUD DE CONFIRMACION OBRAS TERMINADAS.docx',
    'E-4': '5 REVISION DE PRESUPUESTO DE OBRAS.xlsx',
    'E-5': '6 CEDULA REVISION GUATECOMPRAS.xlsx',
    'E-6': '7 PRUEBA FISICA DE OBRAS.docx',
    'E-7': '8 PRUEBA DE COSTOS.xlsx',
    'E-8': '9 CONFIRMACION DE REGISTROS.xlsx',
    'E-9': '10 PARTIDAS DE CIERRE.docx',
    'E-10': '11 PARTIDAS DE AJUSTES.docx',
    'E-11': '12 PARTIDAS DE RECLASIFICACION.docx',
    'E-12': '13 HALLAZGOS.docx',
    'E-13': '14 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Activos Fijos (F)
PATTERN_TO_FILE_F = {
    'F-1': '2 SUMARIA ACTIVOS FIJOS.xlsx',
    'F-2': '3 INTEGRACION.xlsx',
    'F-3': '4 Revisión de títulos de propiedad, facturas y documentos legales.xlsx',
    'F-4': '5 INSPECCION FISICA.xlsx',
    'F-5': '6 PRUEBA DE ADICIONES.xlsx',
    'F-6': '7 PRUEBA DE BAJAS.xlsx',
    'F-7': '8 PRUEBA DE TRASLADOS.xlsx',
    'F-8': '9 METODOS USADOS.xlsx',
    'F-9': '10 DEPRECIACION.xlsx',
    'F-10': '11 PARTIDAS DE AJUSTES.docx',
    'F-11': '12 PARTIDAS DE RECLASIFICACION.docx',
    'F-12': '13 HALLAZGOS DE AUDITORIA.docx',
    'F-13': '14 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Activo Intangible (G)
PATTERN_TO_FILE_G = {
    'G-1': '2 SUMARIA ACTIVO INTANGIBLE.xlsx',
    'G-2': '3 INTEGRACION.xlsx',
    'G-3': '4 REVISION DE CONTRATOS.xlsx',
    'G-4': '5 SOLICITUD DE CONFIRMACION.docx',
    'G-5': '6 CONFIRMACION DE SEGUROS.docx',
    'G-6': '7 REVISIÓN DE SEGUROS PAGADOS.xlsx',
    'G-7': '8 PARTIDAS DE AJUSTES.docx',
    'G-8': '9 PARTIDAS DE RECLASIFICACION.docx',
    'G-9': '10 HALLAZGOS DE AUDITORIA.docx',
    'G-10': '11 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Cuentas por Pagar (H)
PATTERN_TO_FILE_H = {
    'H-1': '2 SUMARIA CUENTAS POR PAGAR.xlsx',
    'H-2': '3 INTEGRACION.xlsx',
    'H-3': '4 INTEGRACION DE PROVEEDORES.xlsx',
    'H-4': '5 PROVEEDORES SELECCIONADOS PARA CONFIRMACION.docx',
    'H-5': '6 OFICIOS CONFIRMACIONES A PROVEEDORES.docx',
    'H-6': '7 CONFIRMACIONES DE PROVEEDORES.docx',
    'H-7': '8 ESTADISTICA DE PROVEEDORES.docx',
    'H-8': '9 CIRCULARIZACION DE PASIVOS.docx',
    'H-9': '10 CONFIRMACION DE ABOGADOS.docx',
    'H-10': '11 RESPUESTA CONFIRMACION DE ABOGADOS.docx',
    'H-11': '12 REVISION DE FACTURAS Y DOCUMENTOS DE RESPALDO.xlsx',
    'H-12': '13 INSPECCION FISICA PROVEEDORES.xlsx',
    'H-13': '14 PRUEBA DE PASIVOS OCULTOS.xlsx',
    'H-14': '15 Prueba de Pagos Posteriores.xlsx',
    'H-15': '16 Prueba de Cálculo de Prestaciones Laborales.xlsx',
    'H-16': '17 PARTIDAS DE AJUSTES.docx',
    'H-17': '18 PARTIDAS DE RECLASIFICACION.docx',
    'H-18': '19 HALLAZGOS DE AUDITORIA.docx',
    'H-19': '20 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Pasivo Largo Plazo (I)
PATTERN_TO_FILE_I = {
    'I-1': '2 SUMARIA PASIVO LARGO PLAZO.xlsx',
    'I-2': '3 ANALISIS DE PRESTAMOS.xlsx',
    'I-3': '4 OFICIO SOLICITUD CONFIRMACION PRESTAMOS.docx',
    'I-4': '5 CONFIRMACION DE PRESTAMOS.docx',
    'I-5': '6 PARTIDAS DE AJUSTES.docx',
    'I-6': '7 PARTIDAS DE RECLASIFICACION.docx',
    'I-7': '8 HALLAZGOS DE AUDITORIA.docx',
    'I-8': '9 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Patrimonio (J)
PATTERN_TO_FILE_J = {
    'J-1': '2 SUMARIA PATRIMONIO.xlsx',
    'J-2': '3 INTEGRACIÓN DEL PATRIMONIO.xlsx',
    'J-3': '4 INTEGRACIÓN DE DIVIDENDOS.xlsx',
    'J-4': '5 Revisión de documentación de transacciones.xlsx',
    'J-5': '6 PARTIDAS DE AJUSTES.docx',
    'J-6': '7 PARTIDAS DE RECLASIFICACION.docx',
    'J-7': '8 HALLAZGOS DE AUDITORIA.docx',
    'J-8': '9 EVIDENCIAS DE HALLAZGOS.docx',
}

# Mapeo de patrones a nombres de archivos específicos para Estado de Resultados (R)
PATTERN_TO_FILE_R = {
    'R-1': '2 SUMARIA ESTADO RESULTADOS.xlsx',
    'R-2': '3 Análisis de tendencias y comparaciones históricas de ingresos.xlsx',
    'R-3': '4 Análisis de tendencias y comparaciones históricas de egresos.xlsx',
    'R-4': '5 Análisis comparativo de registros Ingresos.xlsx',
    'R-5': '6 Análisis comparativo de registros egresos.xlsx',
    'R-6': '7 Prueba Global de Nóminas.xlsx',
    'R-7': '8 PRUEBA DE PLANILLA.xlsx',
    'R-8': '9 VERIFICACION DE DECLARACIONES DE IMPUESTOS.docx',
    'R-9': '10 Prueba Global Seguro Social.xlsx',
    'R-10': '11 PARTIDAS DE AJUSTES.docx',
    'R-11': '12 PARTIDAS DE RECLASIFICACION.docx',
    'R-12': '13 HALLAZGOS DE AUDITORIA.docx',
    'R-13': '14 EVIDENCIAS DE HALLAZGOS.docx',
}

# Diccionario principal que combina todos los mapeos
PATTERN_TO_FILE = {
    **PATTERN_TO_FILE_A,
    **PATTERN_TO_FILE_B,
    **PATTERN_TO_FILE_C,
    **PATTERN_TO_FILE_D,
    **PATTERN_TO_FILE_E,
    **PATTERN_TO_FILE_F,
    **PATTERN_TO_FILE_G,
    **PATTERN_TO_FILE_H,
    **PATTERN_TO_FILE_I,
    **PATTERN_TO_FILE_J,
    **PATTERN_TO_FILE_R,
    # Agregar más según sea necesario
}