from django.contrib import admin
from common.templatetags.filters import format_duration_field
from common.utils import convert_date_str_to_datetime, is_valid_date
from tools.forms import (
    AuditTimeSummaryForm,
    SummaryHoursWorkedForm,
    WorkingPapersStatusesForm,
)
from tools.models import (
    Activity,
    ActivityTotalDaysPerMonth,
    AuditMarks,
    Country,
    CurrencyType,
    CurrentStatus,
    Months,
    SummaryHoursWorked,
    AuditTimeSummary,
    WorkingPapersStatus,
)

from .errors import (
    NullWorkedDaysError,
    NullScheduledDaysError,
    InvalidWorkedDaysError,
    InvalidScheduledDaysError,
    NullWorkedHoursError,
    NullScheduledHoursError,
    InvalidWorkedHoursError,
    InvalidScheduledHoursError,
    NullStartDateError,
    NullEndDateError,
    InvalidStartDateError,
    InvalidEndDateError,
)


class AuditTimeSummaryAdmin(admin.ModelAdmin):
    form = AuditTimeSummaryForm

    fieldsets = (
        (
            "Datos del Resumen de Tiempo Auditoría",
            {"fields": ("appointment_number", "full_name", "position", "observations")},
        ),
        ("Seleccione el auditor", {"fields": ("auditor",)}),
        (
            "Seleccione la auditoría (la auditoría debe estar asignada a el auditor seleccionado, o, el auditor seleccionado debe de ser el jefe de auditoria)",
            {"fields": ("audit",)},
        ),
        (
            "Días programados para la auditoría",
            {"fields": ("scheduled_days_str",)},
        ),
        (
            "Días totales en los que se trabajaron",
            {"fields": ("worked_days_str",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        worked_days = form.cleaned_data.get("worked_days_str")
        scheduled_days = form.cleaned_data.get("scheduled_days_str")
        if not worked_days:
            raise NullWorkedDaysError()
        if not scheduled_days:
            raise NullScheduledDaysError()

        if not isinstance(worked_days, int):
            raise InvalidWorkedDaysError()

        if not isinstance(scheduled_days, int):
            raise InvalidScheduledDaysError()

        worked_days_duration = format_duration_field(int(worked_days), "days")
        scheduled_days_duration = format_duration_field(int(scheduled_days), "days")

        obj.scheduled_days = scheduled_days_duration
        obj.worked_days = worked_days_duration
        super().save_model(request, obj, form, change)


class SummaryHoursWorkedAdmin(admin.ModelAdmin):
    form = SummaryHoursWorkedForm

    fieldsets = (
        (
            "Datos del Resumen de Tiempo Auditoría",
            {"fields": ("month", "observations")},
        ),
        ("Seleccione el auditor", {"fields": ("auditor",)}),
        (
            "Seleccione la auditoría (la auditoría debe estar asignada a el auditor seleccionado, o, el auditor seleccionado debe de ser el jefe de auditoria)",
            {"fields": ("audit",)},
        ),
        (
            "Total de horas programadas",
            {"fields": ("total_scheduled_hours_str",)},
        ),
        (
            "Total de horas trabajadas",
            {"fields": ("total_hours_worked_str",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        worked_hours = form.cleaned_data.get("total_hours_worked_str")
        scheduled_hours = form.cleaned_data.get("total_scheduled_hours_str")
        if not worked_hours:
            raise NullWorkedHoursError()
        if not scheduled_hours:
            raise NullScheduledHoursError()

        if not isinstance(worked_hours, int):
            raise InvalidWorkedHoursError()

        if not isinstance(scheduled_hours, int):
            raise InvalidScheduledHoursError()

        worked_hours_duration = format_duration_field(int(worked_hours), "hours")
        scheduled_hours_duration = format_duration_field(int(scheduled_hours), "hours")

        obj.total_scheduled_hours = scheduled_hours_duration
        obj.total_hours_worked = worked_hours_duration
        super().save_model(request, obj, form, change)


class WorkingPapersStatusesAdmin(admin.ModelAdmin):
    form = WorkingPapersStatusesForm
    fieldsets = (
        (
            "Datos del Estado de Papel de Trabajo",
            {"fields": ("current_status", "working_papers", "reference")},
        ),
        ("Seleccione el auditor", {"fields": ("auditor",)}),
        (
            "Seleccione la auditoría (la auditoría debe estar asignada a el auditor seleccionado, o, el auditor seleccionado debe de ser el jefe de auditoria)",
            {"fields": ("audit",)},
        ),
        ("Fecha de Inicio", {"fields": ("start_date_str",)}),
        ("Fecha de Finalización", {"fields": ("end_date_str",)}),
    )

    def save_model(self, request, obj, form, change):
        start_date = form.cleaned_data.get("start_date_str")
        end_date = form.cleaned_data.get("end_date_str")
        if not start_date:
            raise NullStartDateError()
        if not end_date:
            raise NullEndDateError()

        if not is_valid_date(str(start_date)):
            raise InvalidStartDateError()
        if not is_valid_date(str(end_date)):
            raise InvalidEndDateError()

        start_date_date_time = convert_date_str_to_datetime(str(start_date))

        end_date_date_time = convert_date_str_to_datetime(str(end_date))

        obj.start_date = start_date_date_time
        obj.end_date = end_date_date_time
        super().save_model(request, obj, form, change)


admin.site.register(AuditTimeSummary, AuditTimeSummaryAdmin)
admin.site.register(SummaryHoursWorked, SummaryHoursWorkedAdmin)
admin.site.register(WorkingPapersStatus, WorkingPapersStatusesAdmin)
admin.site.register(CurrentStatus)
admin.site.register(Months)
admin.site.register(AuditMarks)
admin.site.register(Country)
admin.site.register(Activity)
admin.site.register(ActivityTotalDaysPerMonth)
