"""
Mapeos de nomenclatura para documentos de auditoría interna.
Contiene la configuración jerárquica de prefijos y rangos para documentos de procesos.
"""

# Nueva configuración para documentos de auditoría interna
INTERNAL_NOMENCLATURE_MAP = {
    "6 AUDITORIA DE PROCESOS": {
        "1 Operativo": {
            "1 Gestión de Inventarios y Almacenes": {
                "4 Programa de Auditoría.docx": {
                    "prefix": "B",
                    "max_range": 12  # B-6, B-7, B-8, B-9, B-10
                }
            }
        },
        "2 Comercial": {
            "4 Programa de Auditoría.docx": {
                "prefix": "D",
                "max_range": 12  # D-5, D-6, D-7, D-8, D-9
            }
        },
        "3 Financiero": {
            "1 AUDITORIA PROCESOS TESORERIA": {
                "4 Programa de Auditoría.docx": {
                    "prefix": "E",
                    "max_range": 12  # E-5, E-6, E-7, E-8, E-9, E-10
                }
            },
            "2 AUDITORIA PROCESOS CONTABILIDAD": {
                "4 Programa de Auditoría.docx": {
                    "prefix": "F",
                    "max_range": 12  # F-5, F-6, F-7, F-8, F-9, F-10
                }
            },
            "3 AUDITORIA PROCESOS COMPRAS": {
                "4 Programa de Auditoría.docx": {
                    "prefix": "H",
                    "max_range": 12  # H-5, H-6, H-7, H-8, H-9, H-10
                }
            }
        },
        "4 Recursos Humanos": {
            "4 Programa de Auditoría.docx": {
                "prefix": "K",
                "max_range": 12  # K-5, K-6, K-7, K-8, K-9, K-10, K-11
            }
        },
        "5 Tecnología": {
            "4 Programa de Auditoría.docx": {
                "prefix": "L",
                "max_range": 12  # L-5, L-6, L-7, L-8, L-9
            }
        },
        "6 Legal": {
            "4 Programa de Auditoría.docx": {
                "prefix": "M",
                "max_range": 12  # M-5, M-6, M-7, M-8, M-9
            }
        },
        "7 Servicios Públicos": {
            "4 Programa de Auditoría.docx": {
                "prefix": "N",
                "max_range": 12  # N-5, N-6, N-7, N-8, N-9
            }
        },
        "8 Obras Públicas": {
            "4 Programa de Auditoría.docx": {
                "prefix": "O",
                "max_range": 12  # O-5, O-6, O-7, O-8, O-9, O-10
            }
        },
        "9 Gestión de Ahorro": {
            "4 Programa de Auditoría.docx": {
                "prefix": "P",
                "max_range": 12  # P-5, P-6, P-7, P-8, P-9
            }
        },
        "10 Gestión de Créditos": {
            "4 Programa de Auditoría.docx": {
                "prefix": "Q",
                "max_range": 12  # Q-5, Q-6, Q-7, Q-8, Q-9, Q-10, Q-11
            }
        }
    }
}

# Mapa directo de patrones de ruta a prefijos (para búsqueda simplificada)
INTERNAL_PATH_TO_PREFIX_MAP = {
    # Áreas con subáreas específicas 
    "1 operativo/1 gestión de inventarios": "B",
    "3 financiero/1 auditoria procesos tesoreria": "E",
    "3 financiero/2 auditoria procesos contabilidad": "F",
    "3 financiero/3 auditoria procesos compras": "H",
    
    # Áreas sin subáreas (solo el nombre del área)
    "2 comercial": "D",
    "4 recursos humanos": "K",
    "5 tecnología": "L",
    "5 tecnologia": "L",
    "6 legal": "M",
    "7 servicios públicos": "N",
    "7 servicios publicos": "N",
    "8 obras públicas": "O",
    "8 obras publicas": "O",
    "9 gestión de ahorro": "P",
    "9 gestion de ahorro": "P",
    "10 gestión de créditos": "Q",
    "10 gestion de creditos": "Q"
}
