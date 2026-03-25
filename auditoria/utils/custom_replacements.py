def build_custom_replacements(request, audit, fecha_elaboracion=None, fecha_aprobacion=None):
    """
    Reemplazos adicionales controlados por nuestro modal:
    - [AUDITOR_NOMBRE]      -> nombres de assigned_users
    - [SUPERVISOR_NOMBRE]   -> audit.audit_manager
    - [FECHA_ELABORACION]   -> si viene (rol auditor)
    - [FECHA_APROBACION]    -> si viene (rol supervisor)
    """
    replacements = {}

    # Auditor(es)
    auditores_qs = getattr(audit, "assigned_users", None)
    auditores = (auditores_qs.all() if auditores_qs else [])
    auditor_nombre = ", ".join([(u.get_full_name() or u.username) for u in auditores]) or ""

    # Supervisor
    supervisor_nombre = audit.audit_manager.get_full_name() if audit.audit_manager else ""

    replacements["[NOMBRE_AUDITOR]"] = auditor_nombre
    replacements["[NOMBRE_SUPERVISOR]"] = supervisor_nombre

    if fecha_elaboracion:
        replacements["[FECHA_ELABORACION]"] = fecha_elaboracion
    if fecha_aprobacion:
        replacements["[FECHA_APROBACION]"] = fecha_aprobacion

    return replacements
