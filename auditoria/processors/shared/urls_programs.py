"""
Módulo para mapear patrones de hipervínculos a rutas de archivos.
Proporciona funciones para convertir patrones como 'A-1', 'R-10' a rutas de archivos reales.
"""

import os
import logging
import json
from django.conf import settings

logger = logging.getLogger(__name__)

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
    'I-4': '5 CONFIRMACION DE PRESTAMOS.xlsx',
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

# Agregar manejo especial para los programas principales
SPECIAL_PATTERNS = {
    'A-programa': '1 PROGRAMA.docx',
    'B-programa': '1 PROGRAMA DE AUDITORIA CUENTAS POR COBRAR.docx',
    'C-programa': '1 PROGRAMA DE AUDITORIA INVERSIONES.docx',
    'D-programa': '1 PROGRAMA DE AUDITORIA INVENTARIOS.docx',
    'E-programa': '1 PROGRAMA DE AUDITORIA CONSTRUCCIONES EN PROCESO.docx',
    'F-programa': '1 PROGRAMA DE AUDITORIA ACTIVOS FIJOS.docx',
    'G-programa': '1 PROGRAMA DE ACTIVO INTANGIBLE.docx',
    'H-programa': '1 PROGRAMA DE AUDITORIA CUENTAS POR PAGAR.docx',
    'I-programa': '1 PROGRAMA DE AUDITORIA PRESTAMOS POR PAGAR.docx',
    'J-programa': '1 PROGRAMA DE AUDITORIA PATRIMONIO.docx',
    'R-programa': '1 PROGRAMA DE AUDITORIA ESTADO RESULTADOS.docx',
}

# Mapeo de prefijos a sus archivos de programa correspondientes
PREFIX_TO_PROGRAM = {
    'A': '1 PROGRAMA.docx',
    'B': '1 PROGRAMA DE AUDITORIA CUENTAS POR COBRAR.docx',
    'C': '1 PROGRAMA DE AUDITORIA INVERSIONES.docx',
    'D': '1 PROGRAMA DE AUDITORIA INVENTARIOS.docx',
    'E': '1 PROGRAMA DE AUDITORIA CONSTRUCCIONES EN PROCESO.docx',
    'F': '1 PROGRAMA DE AUDITORIA ACTIVOS FIJOS.docx',
    'G': '1 PROGRAMA DE ACTIVO INTANGIBLE.docx',
    'H': '1 PROGRAMA DE AUDITORIA CUENTAS POR PAGAR.docx',
    'I': '1 PROGRAMA DE AUDITORIA PRESTAMOS POR PAGAR.docx',
    'J': '1 PROGRAMA DE AUDITORIA PATRIMONIO.docx',
    'R': '1 PROGRAMA DE AUDITORIA ESTADO RESULTADOS.docx',
}

def get_file_info_from_pattern(pattern, is_internal=False):
    """
    Convierte un patrón (ej: 'A-1', 'R-10') en información necesaria para descargar el archivo.
    
    Args:
        pattern: El patrón de nomenclatura (ej: 'A-1')
        is_internal: Si es True, se busca en templates_base_interna, si no, en templates_base_financiera
        
    Returns:
        dict: Diccionario con la información del archivo o None si no se encuentra
            {
                'folder': Carpeta relativa donde se encuentra el archivo,
                'filename': Nombre del archivo,
                'full_path': Ruta completa del archivo en el sistema de archivos
            }
    """
    if not pattern or '-' not in pattern:
        logger.warning(f"Patrón inválido: {pattern}")
        return None
        
    # Extraer el prefijo (A, B, R, etc.)
    prefix = pattern.split('-')[0]
    
    # Obtener la carpeta base y el patrón según el tipo de auditoría
    if is_internal:
        folder = INTERNAL_PREFIX_TO_FOLDER.get(prefix)
        pattern_to_file = INTERNAL_PATTERN_TO_FILE
        prefix_to_program = INTERNAL_PREFIX_TO_PROGRAM
    else:
        folder = PREFIX_TO_FOLDER.get(prefix)
        pattern_to_file = PATTERN_TO_FILE
        prefix_to_program = PREFIX_TO_PROGRAM
    
    if not folder:
        logger.warning(f"Prefijo no reconocido: {prefix} para {'auditoría interna' if is_internal else 'auditoría financiera'}")
        return None
    
    # Verificar si es un patrón especial
    if pattern in SPECIAL_PATTERNS:
        filename = SPECIAL_PATTERNS[pattern]
    else:
        # Obtener el nombre del archivo para este patrón
        filename = pattern_to_file.get(pattern)
    
    if not filename:
        # Caso especial: si no se encuentra el patrón, podría estar buscando el programa
        if pattern.split('-')[1].lower() == 'programa' or (prefix in 'ABCDEFGHIJR' and pattern not in pattern_to_file):
            filename = prefix_to_program.get(prefix)
            logger.info(f"Usando el programa principal para el patrón: {pattern}")
        else:
            logger.warning(f"No se encontró archivo para el patrón: {pattern}")
            return None
    
    # Construir la ruta completa según el tipo de auditoría
    if is_internal:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_interna')
    else:
        base_path = os.path.join(settings.BASE_DIR, 'static', 'templates_base_financiera')
    
    full_path = os.path.join(base_path, folder, filename)
    
    # Verificar si el archivo existe
    if not os.path.exists(full_path):
        logger.warning(f"El archivo no existe en la ruta: {full_path}")
        # Intentar buscar el archivo de forma más flexible
        from auditoria.views import normalize_text, get_template_path
        template_path = get_template_path(folder, filename, is_internal=is_internal)
        if template_path:
            full_path = template_path
        else:
            logger.error(f"No se pudo encontrar el archivo para el patrón: {pattern}")
            return None
    
    return {
        'folder': folder,
        'filename': filename,
        'full_path': full_path
    }

def get_pattern_from_file(folder, filename):
    """
    Función inversa que obtiene el patrón a partir de la carpeta y nombre de archivo.
    
    Args:
        folder: Carpeta relativa donde se encuentra el archivo
        filename: Nombre del archivo
        
    Returns:
        str: El patrón correspondiente o None si no se encuentra
    """
    # Verificar si es un archivo especial primero
    for pattern, fname in SPECIAL_PATTERNS.items():
        if fname == filename:
            return pattern
    
    # Determinar si es auditoría interna o financiera
    is_internal = '6 auditoria de procesos' in folder.lower()
    
    # Determinar el prefijo basado en la carpeta
    prefix = None
    
    if is_internal:
        prefix_to_folder = INTERNAL_PREFIX_TO_FOLDER
        pattern_to_file = INTERNAL_PATTERN_TO_FILE
        prefix_to_program = INTERNAL_PREFIX_TO_PROGRAM
    else:
        prefix_to_folder = PREFIX_TO_FOLDER
        pattern_to_file = PATTERN_TO_FILE
        prefix_to_program = PREFIX_TO_PROGRAM
    
    for p, f in prefix_to_folder.items():
        if f.lower() in folder.lower():
            prefix = p
            break
    
    if not prefix:
        logger.warning(f"No se pudo determinar el prefijo para la carpeta: {folder}")
        return None
    
    # Buscar el patrón que corresponde a este archivo
    for pattern, file in pattern_to_file.items():
        if file == filename and pattern.startswith(prefix):
            return pattern
    
    # Caso especial para el programa principal
    if filename == prefix_to_program.get(prefix):
        return f"{prefix}-programa"  # Devolver un código especial para el programa
    
    logger.warning(f"No se encontró patrón para el archivo: {folder}/{filename}")
    return None
