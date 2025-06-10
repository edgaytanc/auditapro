class InvalidNoteNotificationError(Exception):
    def __init__(self):
        super().__init__(
            "La nota de la notificación no puede estar vacía o es inválida."
        )


class NotificationDoNotExits(Exception):
    def __init__(self):
        super().__init__("La notificación ingresada no existe.")


class InvalidNotifiedsNotificationError(Exception):
    def __init__(self):
        super().__init__("Debe haber al menos 1 notificado.")


class NotifiedsNotificatonDoNotExitsError(Exception):
    def __init__(self, notifier_id=None):
        if not notifier_id:
            super().__init__("Alguno de los notificados ingresados no existe.")
        else:
            super().__init__(f"El notificado {notifier_id} no existe.")


class InvalidAuditNotificationError(Exception):
    def __init__(self):
        super().__init__("La Auditoria es inválida o está vacía, por favor corregir.")


class AuditNotificationDoNotExitsError(Exception):
    def __init__(self):
        super().__init__("La Auditoria ingresada no existe.")


class InvalidNotifierError(Exception):
    def __init__(self):
        super().__init__("El notificador es inválido.")


class NotifierDoNotExits(Exception):
    def __init__(self):
        super().__init__("El notificador no existe.")


class AuditorInvalidNotifierError(ValueError):
    def __init__(self):
        super().__init__(
            "Los Auditores únicamente pueden notificar a los Jefes de Auditoría."
        )


class SupervisorInvalidNotifierError(ValueError):
    def __init__(self):
        super().__init__(
            "Los Jefes de Auditoría solo pueden notificar a los Auditores."
        )


class AuditNotAssignantToUser(ValueError):
    def __init__(self, user_name=None):
        if not user_name:
            super().__init__(
                "Uno de los usuarios no tiene esta auditoría asignada, así que no se le puede notificar"
            )
        else:
            super().__init__(
                f"El usuario {user_name} no tiene esta auditoría asignada, así que no se le puede notificar"
            )
