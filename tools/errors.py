class NullAppointmentNumberError(Exception):
    def __init__(self):
        super().__init__("El número de nombramiento completo no puede estar vacío.")


class NullFullNameError(Exception):
    def __init__(self):
        super().__init__("El nombre completo no puede estar vacío.")


class NullPositionError(Exception):
    def __init__(self):
        super().__init__("El cargo no puede estar vacío.")


class NullScheduledDaysError(Exception):
    def __init__(self):
        super().__init__("Los días programados no pueden estar vacíos.")


class NullWorkedDaysError(Exception):
    def __init__(self):
        super().__init__("Los días trabajados no pueden estar vacíos.")


class NullReferenceError(Exception):
    def __init__(self):
        super().__init__("La referencia no puede estar vacía.")


class NullWorkinPapersError(Exception):
    def __init__(self):
        super().__init__("Los papeles de trabajo no pueden estar vacíos.")


class NullStartDateError(Exception):
    def __init__(self):
        super().__init__("La fecha de inicio no puede estar vacía.")


class NullEndDateError(Exception):
    def __init__(self):
        super().__init__("La fecha de finalización no puede estar vacía.")


class NullCurrentStatusError(Exception):
    def __init__(self):
        super().__init__("El estado actual no puede estar vacío.")


class NullMonthError(Exception):
    def __init__(self):
        super().__init__("El mes ingresado no puede estar vacío.")


class NullScheduledHoursError(Exception):
    def __init__(self):
        super().__init__("Las horas prrogramadas ingresadas no pueden estar vacías.")


class NullWorkedHoursError(Exception):
    def __init__(self):
        super().__init__("Las horas trabajadas ingresadas no pueden estar vacías.")


class InvalidScheduledDaysError(Exception):
    def __init__(self):
        super().__init__(
            "Los días programados ingresados no pueden contener letras, sólo números enteros."
        )


class InvalidWorkedDaysError(Exception):
    def __init__(self):
        super().__init__(
            "Los días trabajados ingresados no pueden contener letras, sólo números enteros."
        )


class InvalidAppointmentNumberError(Exception):
    def __init__(self):
        super().__init__(
            "El número de nombramiento no puede contener letras ni carácteres especiales, solo números."
        )


class InvalidScheduledHoursError(Exception):
    def __init__(self):
        super().__init__(
            "Las horas programadas no pueden contener letras ni carácteres especiales, solo números."
        )


class InvalidWorkedHoursError(Exception):
    def __init__(self):
        super().__init__(
            "Las horas trabajadas no pueden contener letras ni carácteres especiales, solo números."
        )


class InvalidMonthError(Exception):
    def __init__(self):
        super().__init__("El mes ingresado es inválido.")


class InvalidCurrentStatusError(Exception):
    def __init__(self):
        super().__init__("El estado actual ingresado es inválido.")


class InvalidAtLeastOneFieldError(Exception):
    def __init__(self):
        super().__init__("Debe haber al menos un campo para actualizar.")


class InvalidStartDateError(Exception):
    def __init__(self):
        super().__init__("La fecha de inicio ingresada debe ser formato 'YYYY-MM-DD'.")


class InvalidEndDateError(Exception):
    def __init__(self):
        super().__init__(
            "La fecha de finalización ingresada debe ser formato 'YYYY-MM-DD'."
        )


class CurrentStatusDoesNotExitsError(Exception):
    def __init__(self):
        super().__init__("El estado actual ingresado es inválido o no existe.")


class AuditTimeSummaryDoesNotExitsError(Exception):
    def __init__(self):
        super().__init__(
            "El resumen de tiempo de auditoría ingresado no existe o es inválido."
        )


class WorkingPapersStatusDoesNotExitsError(Exception):
    def __init__(self):
        super().__init__(
            "El estado de papeles de trabajo ingresado no existe o es inválido."
        )


class SummaryHoursWorkedDoesNotExitsError(Exception):
    def __init__(self):
        super().__init__(
            "El resumen de horas trabajadas ingresada no existe o es inválido."
        )


class MonthDoesNotExitsError(Exception):
    def __init__(self):
        super().__init__("El mes ingresado no existe o es inválido.")


class TotalWorkedDaysHigherThanScheduledDaysError(Exception):
    def __init__(self):
        super().__init__(
            "Los días trabajados no pueden exceder la cantidad de los días programados."
        )


class TotalWorkedHoursHigherThanScheduledHoursError(Exception):
    def __init__(self):
        super().__init__(
            "Las horas totales trabajadas no pueden exceder la cantidad total de horas programadas."
        )


class StartDateAfterEndDateError(Exception):
    def __init__(self):
        super().__init__(
            "La fecha de inicio debe ser anterior a la fecha de finalización."
        )


class NullNameAuditMarkError(Exception):
    def __init__(self):
        super().__init__("El nombre de la marca no puede estar vacío.")


class NullDescriptionAuditMarkError(Exception):
    def __init__(self):
        super().__init__("La descripción de la marca no puede estar vacía.")


class NullImageAuditMarkError(Exception):
    def __init__(self):
        super().__init__("La imagen de la marca no puede estar vacía.")


class AuditMarkWithThatNameAlredyExits(Exception):
    def __init__(self):
        super().__init__("Ya existe una marca con ese nombre asociado.")


class AuditMarkWithThatDescriptionAlredyExits(Exception):
    def __init__(self):
        super().__init__("Ya existe una marca con esa descripción asociada.")


class AuditMarkWithThatImageAlredyExits(Exception):
    def __init__(self):
        super().__init__("Ya existe una marca con esa imagen asociada")


class InvalidCurrencyCodeError(Exception):
    def __init__(self):
        super().__init__("El código del tipo de moneda es inválido o está vacío.")


class InvalidCurrencyNameError(Exception):
    def __init__(self):
        super().__init__("El nombre del tipo de moneda es inválido o está vacío")


class InvalidCurrencyCurrencyError(Exception):
    def __init__(self):
        super().__init__("La moneda del tipo de la moneda está vacía o es inválida.")


class InvalidCurrencyError(Exception):
    def __init__(self):
        super().__init__("El tipo de moneda es inválido o está vacío.")


class CurrencyNameAlredyAssignedError(Exception):
    def __init__(self):
        super().__init__("El nombre ingresado ya está asignado a un tipo de moneda.")


class CurrencyCodeAlredyAssignedError(Exception):
    def __init__(self):
        super().__init__("El código ingresado ya está asignado a un tipo de moneda.")


class InvalidCountryError(Exception):
    def __init__(self):
        super().__init__("El país es inválido o está vacío.")


class CurrencyCountryAlredyAssignedError(Exception):
    def __init__(self):
        super().__init__("El país ingresado es .")


class InvalidActivityError(Exception):
    def __init__(self):
        super().__init__("La actividad ingresada no existe o es inválida.")


class NullNameError(Exception):
    def __init__(self):
        super().__init__("El nombre ingresado no puede estar vacío.")


class InvalidTotalDaysError(Exception):
    def __init__(self):
        super().__init__("Los días totales ingresados son inválidos o están vacíos.")


class InvalidYearError(Exception):
    def __init__(self):
        super().__init__("El año ingresado es inválido o están vacíos.")
