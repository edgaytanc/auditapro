"""Catálogo visible del módulo Videos y Guías.

Enlaces de acceso a búsquedas temáticas dentro del canal indicado por el cliente.
Se evita enlazar videos individuales que puedan haber sido retirados.
Las guías se sirven desde los PDF incluidos en la aplicación.
"""

YOUTUBE_CHANNEL = "https://www.youtube.com/@SistemaAudita"
YOUTUBE_VIDEOS = f"{YOUTUBE_CHANNEL}/videos"

VIDEOS = (
    {
        "title": "Revisión de Contratos",
        "eyebrow": "Pregunta a la IA sobre los hallazgos",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=Revisi%C3%B3n%20de%20Contratos",
        "icon": "bi-file-earmark-check",
    },
    {
        "title": "Papeles de Trabajo",
        "eyebrow": "Descarga de informe",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=Papeles%20de%20Trabajo",
        "icon": "bi-journal-text",
    },
    {
        "title": "Informes Automatizados",
        "eyebrow": "Pregunta a la IA sobre el informe",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=Informes%20Automatizados",
        "icon": "bi-file-earmark-bar-graph",
    },
    {
        "title": "Análisis Masivo de Datos",
        "eyebrow": "Analiza grandes volúmenes de información",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=An%C3%A1lisis%20Masivo%20de%20Datos",
        "icon": "bi-database-check",
    },
    {
        "title": "Análisis Predictivo",
        "eyebrow": "Pregunta a la IA con el resumen del análisis",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=An%C3%A1lisis%20Predictivo",
        "icon": "bi-graph-up-arrow",
    },
    {
        "title": "Detección de Fraudes",
        "eyebrow": "Detección de patrones críticos",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=Detecci%C3%B3n%20de%20Fraudes",
        "icon": "bi-shield-check",
    },
)

PRESENTATIONS = (
    {
        "title": "AuditaPro",
        "eyebrow": "Presentación general del sistema",
        "duration": "",
        "url": "https://www.youtube.com/@SistemaAudita/search?query=AuditaPro",
        "icon": "bi-play-btn",
    },
)

GUIDES = (
    {
        "slug": "importar-estados-financieros",
        "title": "Importar Estados Financieros",
        "description": "Importación e integración de estados financieros con los procedimientos analíticos.",
        "pages": 20,
        "filename": "01_importar_estados_financieros.pdf",
        "icon": "bi-file-earmark-spreadsheet",
    },
    {
        "slug": "seleccion-ano-auditoria",
        "title": "Selección del Año de Auditoría",
        "description": "Configuración de los períodos utilizados en los cuadros comparativos de la auditoría.",
        "pages": 2,
        "filename": "02_seleccion_ano_auditoria.pdf",
        "icon": "bi-calendar3",
    },
    {
        "slug": "registro-auditor-individual",
        "title": "Registro del Auditor Individual y Fecha de Elaboración",
        "description": "Registro del responsable y de la fecha de elaboración de los papeles de trabajo.",
        "pages": 3,
        "filename": "03_registro_auditor_individual.pdf",
        "icon": "bi-person-check",
    },
    {
        "slug": "jefe-supervisor-equipo",
        "title": "Jefe/Supervisor y Fecha para Trabajos en Equipo",
        "description": "Uso de los campos de supervisión y fechas cuando la auditoría se realiza en equipo.",
        "pages": 3,
        "filename": "04_jefe_supervisor_equipo.pdf",
        "icon": "bi-people",
    },
    {
        "slug": "referencias-papeles-trabajo",
        "title": "Asignación de Referencias en Papeles de Trabajo",
        "description": "Cómo asignar y utilizar referencias dentro de los documentos de la auditoría.",
        "pages": 7,
        "filename": "05_referencias_papeles_trabajo.pdf",
        "icon": "bi-bookmark-check",
    },
    {
        "slug": "marcas-auditoria",
        "title": "Uso Sistemático de Marcas de Auditoría",
        "description": "Aplicación de marcas de auditoría para documentar y estandarizar las pruebas realizadas.",
        "pages": 7,
        "filename": "06_marcas_auditoria.pdf",
        "icon": "bi-check2-square",
    },
    {
        "slug": "muestreo-tres-opciones",
        "title": "Muestreo de Auditoría con Tres Opciones",
        "description": "Guía del módulo de muestreo y sus alternativas para seleccionar muestras de auditoría.",
        "pages": 11,
        "filename": "07_muestreo_tres_opciones.pdf",
        "icon": "bi-bullseye",
    },
    {
        "slug": "automatizacion-plantillas",
        "title": "Automatización de Plantillas",
        "description": "Uso de las plantillas automatizadas disponibles dentro del flujo de trabajo.",
        "pages": 3,
        "filename": "08_automatizacion_plantillas.pdf",
        "icon": "bi-magic",
    },
)

GUIDES_BY_SLUG = {guide["slug"]: guide for guide in GUIDES}
