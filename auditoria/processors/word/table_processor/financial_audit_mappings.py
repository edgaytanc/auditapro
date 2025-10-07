"""
Mapeos de nomenclatura para documentos de auditoría financiera.
Contiene la configuración de prefijos y rangos para documentos estándar.
"""

# Configuración original para documentos estándar de auditoría financiera
FINANCIAL_NOMENCLATURE_MAP = {
    "1 programa.docx": {"prefix": "A", "max_range": 18},
    "1 programa de auditoria cuentas por cobrar.docx": {"prefix": "B", "max_range": 16},
    "1 programa de auditoria inversiones.docx": {"prefix": "C", "max_range": 6},
    "1 programa de auditoria inventarios.docx": {"prefix": "D", "max_range": 16},
    "1 programa de auditoria construcciones en proceso.docx": {"prefix": "E", "max_range": 13},
    "1 programa de auditoria activos fijos.docx": {"prefix": "F", "max_range": 13},
    "1 programa de activo intangible.docx": {"prefix": "G", "max_range": 10},
    "1 programa de auditoria cuentas por pagar.docx": {"prefix": "H", "max_range": 19},
    "1 programa de auditoria prestamos por pagar.docx": {"prefix": "I", "max_range": 8},
    "1 programa de auditoria patrimonio.docx": {"prefix": "J", "max_range": 8},
    "1 programa de auditoria estado resultados.docx": {"prefix": "R", "max_range": 13},
}
