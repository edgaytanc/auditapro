# Mapeo de prefijos a carpetas para auditoría interna (proceso)
INTERNAL_PREFIX_TO_FOLDER = {
    'B': '6 AUDITORIA DE PROCESOS/1 Operativo/1 Gestión de inventarios y almacenes/5 PRUEBAS DE AUDITORIA',
    'D': '6 AUDITORIA DE PROCESOS/2 Comercial/5 PRUEBAS',
    'E': '6 AUDITORIA DE PROCESOS/3 Financiero/1 AUDITORIA PROCESOS TESORERIA/5 PRUEBAS SUSTANTIVAS Y FRAUDE',
    'F': '6 AUDITORIA DE PROCESOS/3 Financiero/2 AUDITORIA PROCESOS CONTABILIDAD/5 PRUEBAS',
    'H': '6 AUDITORIA DE PROCESOS/3 Financiero/3 AUDITORIA PROCESOS COMPRAS/5 PRUEBAS',
    'K': '6 AUDITORIA DE PROCESOS/4 Recursos Humanos/5 PRUEBAS',
    'L': '6 AUDITORIA DE PROCESOS/5 Tecnologia/5 PRUEBAS',
    'M': '6 AUDITORIA DE PROCESOS/6 Legal/5 PRUEBAS',
    'N': '6 AUDITORIA DE PROCESOS/7 Servicios Públicos/5 PRUEBAS',
    'O': '6 AUDITORIA DE PROCESOS/8 Obras Públicas/5 PRUEBAS',
    'P': '6 AUDITORIA DE PROCESOS/9 Gestión de Ahorro/5 PRUEBAS',
    'Q': '6 AUDITORIA DE PROCESOS/10 Gestión de Créditos/5 PRUEBAS',
}

# Mapeo de patrones para auditoría de procesos (inventarios - B)
INTERNAL_PATTERN_TO_FILE_B = {
    'B-6': '1 Inspección Física.docx',
    'B-7': '2 Conciliacion Saldos.docx',
    'B-8': '3 Análisis de transacciones.docx',
    'B-9': '4 Revisión de documentación.docx',
    'B-10': '5 Identificación de riesgos.docx',
}

# Mapeo de patrones para auditoría de procesos (comercial - D)
INTERNAL_PATTERN_TO_FILE_D = {
    'D-5': '1 Pruebas de Ventas.docx',
    'D-6': '2 Analizar Transaciones.docx',
    'D-7': '3 Revisar segregación de funciones.docx',
    'D-8': '4 Conciliar periódicamente cifras.docx',
    'D-9': '5 Evaluar Politicas.docx',
}

# Mapeo de patrones para auditoría de procesos (tesorería - E)
INTERNAL_PATTERN_TO_FILE_E = {
    'E-5': '1 Revisar políticas y procedimientos.docx',
    'E-6': '2 Examinar el cumplimiento.docx',
    'E-7': '3 Revisar conciliaciones bancarias.docx',
    'E-8': '4 Pruebas pagos duplicados.docx',
    'E-9': '5 Identificar señales de fraude.docx',
    'E-10': '6 Revisar reportes flujo de caja.docx',
}

# Mapeo de patrones para auditoría de procesos (contabilidad - F)
INTERNAL_PATTERN_TO_FILE_F = {
    'F-5': '1 Revisión Conciliaciones Bancarias.docx',
    'F-6': '2 Pruebas de Integridad.docx',
    'F-7': '3 Pruebas de Validación.docx',
    'F-8': '4 Pruebas de Análisis.docx',
    'F-9': '5 Pruebas de Confirmaciones externas.docx',
    'F-10': '6 Pruebas Revisión de Accesos.docx',
}

# Mapeo de patrones para auditoría de procesos (compras - H)
INTERNAL_PATTERN_TO_FILE_H = {
    'H-5': '1 Pruebas  Verificar integridad.docx',
    'H-6': '2 Pruebas de Control.docx',
    'H-7': '3 Comprobar segregación de funciones.docx',
    'H-8': '4 Revisar cumplimiento de políticas.docx',
    'H-9': '5 Conciliar las facturas.docx',
    'H-10': '6 Verificación Física de Empresas.docx',
}

# Mapeo de patrones para auditoría de procesos (RRHH - K)
INTERNAL_PATTERN_TO_FILE_K = {
    'K-5': '1 Pruebas de Validación Nómina.docx',
    'K-6': '2 Revisión Beneficios y Deducciones.docx',
    'K-7': '3 Verificación de Personal Fantasma.docx',
    'K-8': '4 Revisión de Contratos Laborales.docx',
    'K-9': '5 Prueba de Vacaciones y Licencias.docx',
    'K-10': '6 Revisión  Procesos de Reclutamiento.docx',
    'K-11': '7 Pruebas de Detección Pagos Duplicados.docx',
}

# Mapeo de patrones para auditoría de procesos (Tecnología - L)
INTERNAL_PATTERN_TO_FILE_L = {
    'L-5': '1 Pruebas Evaluación Control de Accesos.docx',
    'L-6': '2 Pruebas Revisión Incidentes de Seguridad.docx',
    'L-7': '3 Pruebas Validación de Actualizaciones Sistemas.docx',
    'L-8': '4 Pruebas Mantenimiento de Infraestructura.docx',
    'L-9': '5 Pruebas Detección de Accesos Indebidos.docx',
}

# Mapeo de patrones para auditoría de procesos (Legal - M)
INTERNAL_PATTERN_TO_FILE_M = {
    'M-5': '1 Pruebas Revisión Solicitudes de Contrato.docx',
    'M-6': '2 Pruebas Evaluación de Contratos Formalizados.docx',
    'M-7': '3 Pruebas Gestión de Litigios.docx',
    'M-8': '4 Pruebas de Cumplimiento Normativo.docx',
    'M-9': '5 Pruebas Gestión de Expedientes Legales.docx',
}

# Mapeo de patrones para auditoría de procesos (Servicios Públicos - N)
INTERNAL_PATTERN_TO_FILE_N = {
    'N-5': '1 Validar solicitudes.docx',
    'N-6': '2 Verificar calidad y cumplimiento.docx',
    'N-7': '3 Revisar sistema de reclamos y sugerencias.docx',
    'N-8': '4 Verificar alineación de  operaciones.docx',
    'N-9': '5 Revisión registros de mantenimiento.docx',
}

# Mapeo de patrones para auditoría de procesos (Obras Públicas - O)
INTERNAL_PATTERN_TO_FILE_O = {
    'O-5': '1 Verificar expedientes.docx',
    'O-6': '2 Revisar licitaciones públicas.docx',
    'O-7': '3 Analizar avances financieros y físicos.docx',
    'O-8': '4 Inspeccionar calidad de materiales.docx',
    'O-9': '5 Revisar pagos.docx',
    'O-10': '6 Inspección física al proveedor.docx',
}

# Mapeo de patrones para auditoría de procesos (Gestión de Ahorro - P)
INTERNAL_PATTERN_TO_FILE_P = {
    'P-5': '1 Revisión de solicitudes.docx',
    'P-6': '2 Verificación autorizaciones.docx',
    'P-7': '3 Pruebas Evaluación de permisos.docx',
    'P-8': '4 Pruebas cuentas de ahorro inactivas.docx',
    'P-9': '5 Pruebas de Pagos.docx',
}

# Mapeo de patrones para auditoría de procesos (Gestión de Créditos - Q)
INTERNAL_PATTERN_TO_FILE_Q = {
    'Q-5': '1 Verificación Solicitudes de Crédito.docx',
    'Q-6': '2 Evaluación Crediticia.docx',
    'Q-7': '3 Evaluación Aprobación de Créditos.docx',
    'Q-8': '4 Inspección de Cartera.docx',
    'Q-9': '5 Revisión de Créditos en Mora.docx',
    'Q-10': '6 Análisis Registros Contables.docx',
    'Q-11': '7 Detección de Indicios de Fraude.docx',
}

# Mapeo de programas para auditoría interna
INTERNAL_PREFIX_TO_PROGRAM = {
    'B': '4 Programa de Auditoría.docx',
    'D': '4 Programa de Auditoría.docx',
    'E': '4 Programa de Auditoría.docx',
    'F': '4 Programa de Auditoría.docx',
    'H': '4 Programa de Auditoría.docx',
    'K': '4 Programa de Auditoría.docx',
    'L': '4 Programa de Auditoría.docx',
    'M': '4 Programa de Auditoría.docx',
    'N': '4 Programa de Auditoría.docx',
    'O': '4 Programa de Auditoría.docx',
    'P': '4 Programa de Auditoría.docx',
    'Q': '4 Programa de Auditoría.docx',
}

# Diccionario que combina todos los mapeos de patrones internos
INTERNAL_PATTERN_TO_FILE = {
    **INTERNAL_PATTERN_TO_FILE_B,
    **INTERNAL_PATTERN_TO_FILE_D,
    **INTERNAL_PATTERN_TO_FILE_E,
    **INTERNAL_PATTERN_TO_FILE_F,
    **INTERNAL_PATTERN_TO_FILE_H,
    **INTERNAL_PATTERN_TO_FILE_K,
    **INTERNAL_PATTERN_TO_FILE_L,
    **INTERNAL_PATTERN_TO_FILE_M,
    **INTERNAL_PATTERN_TO_FILE_N,
    **INTERNAL_PATTERN_TO_FILE_O,
    **INTERNAL_PATTERN_TO_FILE_P,
    **INTERNAL_PATTERN_TO_FILE_Q,
}