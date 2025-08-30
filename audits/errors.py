class InvalidAuditTitleError(Exception):
    def __init__(self):
        super().__init__("El título de la auditoria no puede ser vacío o es inválido.")


class InvalidAuditCompanyError(Exception):
    def __init__(self):
        super().__init__(
            "El nombre de la compañía de la auditoria no puede ser vacío o es inválido."
        )


class InvalidAuditAuditorsError(Exception):
    def __init__(self):
        super().__init__("Los auditores asignados son inválidos o no existen.")


class InvalidAuditSupervisoresError(Exception):
    def __init__(self):
        super().__init__("Los supervisores asignados no existen o son inválidos.")


class AssignedAuditsNullError(Exception):
    def __init__(self):
        super().__init__("Debe seleccionar al menos un auditor para asignar.")


class AuditDoNotExits(Exception):
    def __init__(self, audit_id=None):
        if not audit_id:
            super().__init__("La auditoría ingresada no existe.")
        else:
            super().__init__(f"La auditoría {audit_id} ingresada no existe.")


class NullAuditError(Exception):
    def __init__(self):
        super().__init__("La auditoría ingresada no puede estar vacía.")


class AuditManagerDoNotExits(Exception):
    def __init__(self):
        super().__init__("El jefe de auditoría no existe.")


class UserAlredyHaveAssignamentAuditError(Exception):
    def __init__(self, user_username=None):
        if user_username:
            super().__init__(
                f"El usuario {user_username} ya tiene asignada las auditorías ingresadas."
            )
        else:
            super().__init__("El usuario ya tiene asignada las auditorías ingresadas.")


class AuditManagerUnauthorized(Exception):
    def __init__(self):
        super().__init__(
            "El jefe de auditoría para esta auditoría no es el que está registrado."
        )


class AuditsNullError(Exception):
    def __init__(self):
        super().__init__("Debe ingresar al menos una Auditoría.")


class InvalidAuditIdentidadError(Exception):
    def __init__(self):
        super().__init__("La identidad de la auditoría no puede estar vacía o es inválida.")


class InvalidAuditDateError(Exception):
    def __init__(self):
        super().__init__("Las fechas de inicio y final de la auditoría no pueden estar vacías o son inválidas.")
