"""
Catálogo base de los 110 papeles de trabajo.

La guía define:
- 22 áreas.
- 5 papeles por área.
"""

WORKPAPER_STATUS_DEFINITIONS = [
    ("pending", "Pendiente"),
    ("prepared", "Preparado"),
    ("in_progress", "En Proceso"),
    ("in_review", "En Revisión"),
    ("approved", "Aprobado"),
]


WORKPAPER_AREAS = [
    ("A", "Efectivo y Bancos"),
    ("B", "Cuentas por Cobrar"),
    ("C", "Estimación de Cuentas Incobrables"),
    ("D", "Inventarios"),
    ("E", "Activos Fijos"),
    ("F", "Depreciación Acumulada"),
    ("G", "Inversiones Financieras"),
    ("H", "Otros Activos"),
    ("I", "Cuentas por Pagar"),
    ("J", "Préstamos por Pagar"),
    ("K", "Impuestos por Pagar"),
    ("L", "Provisiones Laborales"),
    ("M", "Nómina y Prestaciones Sociales"),
    ("N", "Otros Pasivos"),
    ("O", "Contingencias y Compromisos"),
    ("P", "Patrimonio"),
    ("Q", "Ingresos"),
    ("R", "Costo de Ventas"),
    ("S", "Gastos de Operación"),
    ("T", "Gastos Financieros"),
    ("U", "Partes Relacionadas"),
    ("V", "Hechos Posteriores"),
]


WORKPAPER_TYPES = [
    (
        "100",
        "Cédula Sumaria de {area}",
        "Proyecto Inicial",
    ),
    (
        "110",
        "Análisis y Conciliación de {area}",
        "Evaluación de Control",
    ),
    (
        "120",
        "Confirmación / Circularización de {area}",
        "Pruebas Sustantivas",
    ),
    (
        "130",
        "Prueba de Corte de {area}",
        "Pruebas Sustantivas",
    ),
    (
        "140",
        "Revisión de Documentación Soporte de {area}",
        "Finalización",
    ),
]


def build_workpaper_catalog():
    """
    Construye los 110 papeles definidos por la guía.
    """

    catalog = []

    for area_code, area_name in WORKPAPER_AREAS:
        for suffix, title_template, phase in WORKPAPER_TYPES:
            reference = f"{area_code}-{suffix}"

            catalog.append({
                "reference": reference,
                "working_papers": (
                    title_template.format(
                        area=area_name
                    )
                ),
                "phase": phase,
                "area": area_name,
            })

    return catalog


WORKPAPER_CATALOG = build_workpaper_catalog()


PHASE_BY_SUFFIX = {
    suffix: phase
    for suffix, _title, phase in WORKPAPER_TYPES
}


def get_workpaper_phase(reference):
    """
    Obtiene la fase a partir de la referencia.
    """

    reference = str(
        reference or ""
    ).strip()

    suffix = (
        reference.rsplit(
            "-",
            1,
        )[-1]
    )

    return PHASE_BY_SUFFIX.get(
        suffix,
        "Sin clasificar",
    )