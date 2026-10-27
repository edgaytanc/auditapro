PERMANENT_FILE_SECTIONS = [
    ("general", "1. Información General"),
    ("organization", "2. Estructura Organizacional"),
    ("regulations", "3. Leyes y Regulaciones"),
    ("operations", "4. Planificación de Operaciones"),
    ("administrative", "5. Información Administrativa"),
    (
        "financial",
        (
            "6. Información Contable, "
            "Presupuestaria y Financiera"
        ),
    ),
]


def build_default_entries(audit):
    """
    Catálogo inicial del Archivo Permanente.

    Solo automatiza datos que realmente existen
    en el modelo Audit.
    """

    period = (
        audit.periodo_auditado.strip()
        if audit.periodo_auditado
        else ""
    )

    currency = (
        getattr(
            audit,
            "moneda",
            "",
        )
        or ""
    )

    rows = [
        # =====================================================
        # 1. Información General
        # =====================================================
        (
            "general",
            "entity_data",
            "legal_name",
            "Razón Social",
            {
                "value": (
                    audit.identidad
                    or ""
                ),
            },
            "automatic",
            (
                "Tomado de la entidad registrada "
                "en la auditoría."
            ),
        ),
        (
            "general",
            "entity_data",
            "tax_id",
            "NIT",
            {
                "value": "",
            },
            "manual",
            (
                "Registrar el identificador "
                "tributario vigente."
            ),
        ),
        (
            "general",
            "entity_data",
            "audited_period",
            "Período Auditado",
            {
                "value": period,
            },
            "automatic",
            (
                "Tomado del período configurado "
                "en la auditoría."
            ),
        ),
        (
            "general",
            "entity_data",
            "tax_regime",
            "Régimen Fiscal",
            {
                "value": "",
            },
            "manual",
            (
                "Registrar el régimen indicado "
                "en la constancia fiscal."
            ),
        ),
        (
            "general",
            "entity_data",
            "address",
            "Dirección",
            {
                "value": "",
            },
            "manual",
            (
                "Registrar la dirección fiscal "
                "completa."
            ),
        ),
        (
            "general",
            "entity_data",
            "legal_representative",
            "Representante Legal",
            {
                "value": "",
            },
            "manual",
            (
                "Registrar el representante "
                "legal vigente."
            ),
        ),
        (
            "general",
            "entity_data",
            "incorporation_date",
            "Fecha de Constitución",
            {
                "value": "",
            },
            "manual",
            (
                "Registrar la fecha de la "
                "escritura de constitución."
            ),
        ),

        # =====================================================
        # 2. Estructura Organizacional
        # =====================================================
        (
            "organization",
            "key_positions",
            "general_manager",
            "Gerente General",
            {
                "name": "",
            },
            "manual",
            (
                "Confirmar nombre y función "
                "con el cliente."
            ),
        ),
        (
            "organization",
            "key_positions",
            "general_accountant",
            "Contador General",
            {
                "name": "",
            },
            "manual",
            (
                "Confirmar nombre y función "
                "con el cliente."
            ),
        ),
        (
            "organization",
            "key_positions",
            "internal_control_manager",
            "Encargado de Control Interno",
            {
                "name": "",
            },
            "manual",
            (
                "Registrar quién realiza esta "
                "función."
            ),
        ),
        (
            "organization",
            "key_positions",
            "sales_manager",
            "Gerente de Ventas",
            {
                "name": "",
            },
            "manual",
            (
                "Confirmar nombre y línea "
                "de reporte."
            ),
        ),

        # =====================================================
        # 3. Leyes y Regulaciones
        # =====================================================
        (
            "regulations",
            "legal_framework",
            "commercial_code",
            "Código de Comercio",
            {
                "application": "",
            },
            "automatic",
            (
                "Describir cómo aplica a la "
                "constitución y operación."
            ),
        ),
        (
            "regulations",
            "legal_framework",
            "income_tax_law",
            (
                "Ley del Impuesto sobre "
                "la Renta"
            ),
            {
                "application": "",
            },
            "automatic",
            (
                "Indicar régimen y tasa "
                "aplicable."
            ),
        ),
        (
            "regulations",
            "legal_framework",
            "vat_law",
            "Ley del IVA",
            {
                "application": "",
            },
            "automatic",
            (
                "Indicar obligaciones y condición "
                "de retención."
            ),
        ),
        (
            "regulations",
            "legal_framework",
            "accounting_framework",
            "Marco Contable Aplicable",
            {
                "application": "",
            },
            "automatic",
            (
                "Confirmar NIIF, NIIF para PYMES "
                "u otro marco."
            ),
        ),

        # =====================================================
        # 4. Planificación de Operaciones
        # =====================================================
        (
            "operations",
            "operating_cycles",
            "sales_cycle",
            "Ventas",
            {
                "responsible": "",
                "cycle": "",
            },
            "manual",
            (
                "Registrar responsable y "
                "frecuencia del ciclo."
            ),
        ),
        (
            "operations",
            "operating_cycles",
            "purchases_cycle",
            "Compras",
            {
                "responsible": "",
                "cycle": "",
            },
            "manual",
            (
                "Registrar responsable y "
                "frecuencia del ciclo."
            ),
        ),
        (
            "operations",
            "operating_cycles",
            "production_cycle",
            "Producción",
            {
                "responsible": "",
                "cycle": "",
            },
            "manual",
            (
                "Registrar No aplica cuando "
                "la entidad no produce."
            ),
        ),

        # =====================================================
        # 5. Información Administrativa
        # =====================================================
        (
            "administrative",
            "legal_documents",
            "incorporation_deed",
            "Escritura de Constitución",
            {
                "status": "",
            },
            "manual",
            (
                "Verificar contra el documento "
                "vigente."
            ),
        ),
        (
            "administrative",
            "legal_documents",
            "commercial_license",
            "Patente o Registro de Comercio",
            {
                "status": "",
            },
            "manual",
            (
                "Confirmar que la actividad inscrita "
                "coincida con la real."
            ),
        ),
        (
            "administrative",
            "legal_documents",
            "tax_registry",
            "Registro Tributario Actualizado",
            {
                "status": "",
            },
            "manual",
            (
                "Verificar la constancia fiscal "
                "más reciente."
            ),
        ),
        (
            "administrative",
            "legal_documents",
            "municipal_license",
            "Licencia Municipal",
            {
                "status": "",
            },
            "manual",
            (
                "Registrar Vigente, Por renovar "
                "o Vencido."
            ),
        ),

        # =====================================================
        # 6. Información Financiera
        # =====================================================
        (
            "financial",
            "general_financial_data",
            "currency",
            "Moneda de Presentación",
            {
                "value": currency,
            },
            "automatic",
            (
                "Tomado de la moneda configurada "
                "en la auditoría."
            ),
        ),
        (
            "financial",
            "bank_accounts",
            "bank_account_1",
            "Cuenta Bancaria 1",
            {
                "bank": "",
                "account_number": "",
                "account_type": "",
                "balance": "",
                "currency": currency,
            },
            "manual",
            (
                "Registrar los datos de la "
                "confirmación bancaria."
            ),
        ),
        (
            "financial",
            "income_statement",
            "net_revenue",
            "Ingresos Netos",
            {
                "actual": "",
                "budgeted": "",
            },
            "manual",
            (
                "Registrar valores reales "
                "y presupuestados."
            ),
        ),
        (
            "financial",
            "income_statement",
            "cost_of_sales",
            "Costo de Ventas",
            {
                "actual": "",
                "budgeted": "",
            },
            "manual",
            (
                "Registrar valores reales "
                "y presupuestados."
            ),
        ),
        (
            "financial",
            "income_statement",
            "operating_expenses",
            "Gastos Operativos",
            {
                "actual": "",
                "budgeted": "",
            },
            "manual",
            (
                "Registrar valores reales "
                "y presupuestados."
            ),
        ),
        (
            "financial",
            "income_statement",
            "net_income",
            "Utilidad Neta",
            {
                "actual": "",
                "budgeted": "",
            },
            "manual",
            (
                "Registrar valores reales "
                "y presupuestados."
            ),
        ),
        (
            "financial",
            "financial_ratios",
            "current_ratio",
            "Liquidez Corriente",
            {
                "value": "",
                "reference": "> 1.5",
                "evaluation": "",
            },
            "automatic",
            (
                "Se completará desde la información "
                "financiera disponible."
            ),
        ),
        (
            "financial",
            "financial_ratios",
            "quick_ratio",
            "Prueba Ácida",
            {
                "value": "",
                "reference": "> 1.0",
                "evaluation": "",
            },
            "automatic",
            (
                "Se completará desde la información "
                "financiera disponible."
            ),
        ),
        (
            "financial",
            "financial_ratios",
            "debt_ratio",
            "Endeudamiento",
            {
                "value": "",
                "reference": "< 60%",
                "evaluation": "",
            },
            "automatic",
            (
                "Se completará desde la información "
                "financiera disponible."
            ),
        ),
    ]

    return [
        {
            "section": section,
            "group_key": group_key,
            "row_key": row_key,
            "title": title,
            "data": data,
            "origin": origin,
            "guide": guide,
            "sort_order": index * 10,
        }
        for index, (
            section,
            group_key,
            row_key,
            title,
            data,
            origin,
            guide,
        ) in enumerate(
            rows,
            start=1,
        )
    ]