"""Catálogo visible del módulo Videos y Guías.

No contiene lógica de negocio ni modifica datos del sistema. Los enlaces de video
provienen del archivo de enlaces entregado junto con el módulo y las guías se
sirven desde archivos PDF incluidos en esta misma aplicación.
"""

YOUTUBE_CHANNEL = "https://www.youtube.com/@SistemaAudita"
YOUTUBE_VIDEOS = f"{YOUTUBE_CHANNEL}/videos"

VIDEOS = (
    {
        "title": "Revisión de Contratos",
        "eyebrow": "Pregunta a la IA sobre los hallazgos",
        "duration": "3:17",
        "url": "https://www.youtube.com/watch?v=U6n272pMbLM&t=16s",
        "icon": "bi-file-earmark-check",
    },
    {
        "title": "Papeles de Trabajo",
        "eyebrow": "Descarga de informe",
        "duration": "3:00",
        "url": "https://www.youtube.com/watch?v=LclNrYZyoyk&t=11s",
        "icon": "bi-journal-text",
    },
    {
        "title": "Informes Automatizados",
        "eyebrow": "Pregunta a la IA sobre el informe",
        "duration": "3:13",
        "url": "https://www.youtube.com/watch?v=YoOEwdrE_U0&t=4s",
        "icon": "bi-file-earmark-bar-graph",
    },
    {
        "title": "Análisis Masivo de Datos",
        "eyebrow": "Analiza grandes volúmenes de información",
        "duration": "3:00",
        "url": "https://www.youtube.com/watch?v=vFZlQi6VioA",
        "icon": "bi-database-check",
    },
    {
        "title": "Análisis Predictivo",
        "eyebrow": "Pregunta a la IA con el resumen del análisis",
        "duration": "2:38",
        "url": "https://www.youtube.com/watch?v=Cgkt-pN-sSQ&t=12s",
        "icon": "bi-graph-up-arrow",
    },
    {
        "title": "Detección de Fraudes",
        "eyebrow": "Detección de patrones críticos",
        "duration": "2:56",
        "url": "https://www.youtube.com/watch?v=O5kkLNW-9dg",
        "icon": "bi-shield-check",
    },
)

PRESENTATIONS = (
    {
        "title": "AuditaPro",
        "eyebrow": "Presentación general del sistema",
        "duration": "8:33",
        "url": "https://www.youtube.com/watch?v=8SWHj2sF7NI&t=242s",
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
