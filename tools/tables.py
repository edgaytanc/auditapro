from datetime import datetime, timedelta
import django_tables2 as tables
from common.templatetags.filters import format_duration, format_duration_field
from tools.models import (
    Activity,
    AuditMarks,
    AuditTimeSummary,
    SummaryHoursWorked,
    WorkingPapersStatus,
)
from django.utils import formats
import django_tables2 as tables


class BaseTable(tables.Table):
    select = tables.TemplateColumn(
        '<input type="checkbox" class="btn-checkbox" aria-checked="false">',
        verbose_name="",
        attrs={"td": {"class": "td-select"}, "th": {"class": "th-select"}},
    )

    actions = tables.TemplateColumn(
        verbose_name="",
        template_code="""
        <div class="dropdown">
            <button style="background-color: transparent; border: none; outline:none" type="button"
                    data-bs-toggle="dropdown" aria-expanded="false">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
                     xmlns="http://www.w3.org/2000/svg">
                    <path
                        d="M8 12C8 13.1046 7.10457 14 6 14C4.89543 14 4 13.1046 4 12C4 10.8954 4.89543 10 6 10C7.10457 10 8 10.8954 8 12Z"
                        fill="currentColor" />
                    <path
                        d="M14 12C14 13.1046 13.1046 14 12 14C10.8954 14 10 13.1046 10 12C10 10.8954 10.8954 10 12 10C13.1046 10 14 10.8954 14 12Z"
                        fill="currentColor" />
                    <path
                        d="M18 14C19.1046 14 20 13.1046 20 12C20 10.8954 19.1046 10 18 10C16.8954 10 16 10.8954 16 12C16 13.1046 16.8954 14 18 14Z"
                        fill="currentColor" />
                </svg>
            </button>
            <ul class="dropdown-menu">
                <li><a class="dropdown-item" href="{% url record.edit_url record.id %}">Ver Más</a></li>
                <li><button class="btn dropdown-item text-danger" data-bs-toggle="modal" data-bs-target="#confirm-delete-modal{{ record.id }}">Eliminar</button></li>
            </ul>
        </div>

        <div class="modal fade" id="confirm-delete-modal{{ record.id }}" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="static-confirm-delete-modal{{ record.id }}-label" aria-hidden="true">
            <form id="delete_register{{ record.id }}_form" method="post" action="{% url record.delete_url record.id %}" class="d-none">
                {% csrf_token %}
            </form>
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="static-backdrop-confirm-delete-modal{{ record.id }}">Borrar Registro</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger fs-6" role="alert">
                            ¿Está seguro de borrar el registro con el valor: {{ record.confirmation_field }} ?
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-outline" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-danger" form="delete_register{{ record.id }}_form">Sí, Borrar</button>
                    </div>
                </div>
            </div>
        </div>
        """,
        attrs={"td": {"class": "td-options"}, "th": {"class": "th-options"}},
    )

    class Meta:
        abstract = True
        template_name = "django_tables2/bootstrap.html"
        attrs = {"class": "custom-table"}
        orderable = False

    def __init__(
        self,
        data,
        delete_url="default_delete_url",
        edit_url="default_edit_url",
        confirmation_field="default_confirmation_field",
        *args,
        **kwargs,
    ):
        super().__init__(data, *args, **kwargs)
        self.delete_url = delete_url

        for record in self.data:
            record.edit_url = edit_url
            record.delete_url = delete_url
            record.confirmation_field = getattr(record, confirmation_field, "")


class BaseAuditTimeSummaryTable(tables.Table):
    appointment_number = tables.Column(verbose_name="Nombramiento no.")
    full_name = tables.Column(
        verbose_name="Nombre completo",
        accessor="assigned_auditor.get_full_name",
        orderable=False,
    )
    position = tables.Column(verbose_name="Posición", accessor="assigned_auditor.role")
    scheduled_days = tables.Column(verbose_name="Días programados")
    worked_days = tables.Column(verbose_name="Días trabajados")
    differences = tables.Column(verbose_name="Diferencias")
    observations = tables.Column(verbose_name="Observaciones")

    class Meta(BaseTable.Meta):
        model = AuditTimeSummary
        fields = (
            "appointment_number",
            "full_name",
            "position",
            "scheduled_days",
            "worked_days",
            "differences",
            "observations",
        )

    def render_scheduled_days(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"

    def render_worked_days(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"

    def render_differences(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"


class BaseSummaryHoursWorkedTable(tables.Table):
    observations = tables.Column(verbose_name="Observaciones")
    differences = tables.Column(verbose_name="Diferencias")
    total_hours_worked = tables.Column(verbose_name="Total de horas trabajadas")
    total_scheduled_hours = tables.Column(verbose_name="Total de horas programadas")
    month = tables.Column(verbose_name="Mes")

    class Meta(BaseTable.Meta):
        model = SummaryHoursWorked
        fields = (
            "month",
            "total_scheduled_hours",
            "total_hours_worked",
            "differences",
            "observations",
        )

    def render_total_scheduled_hours(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"

    def render_total_hours_worked(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"

    def render_differences(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"


class BaseWorkingPapersStatusesTable(tables.Table):
    working_papers = tables.Column(verbose_name="Papeles de Trabajo")
    observations = tables.Column(verbose_name="Observaciones")
    reference = tables.Column(verbose_name="Ref")
    start_date = tables.Column(verbose_name="Fecha de Inicio")
    end_date = tables.Column(verbose_name="Fecha de Finalización")
    current_status = tables.TemplateColumn(
        verbose_name="Estado Actual",
        template_code="{{ record.current_status }}",
        orderable=False,
    )

    class Meta(BaseTable.Meta):
        model = WorkingPapersStatus
        fields = (
            "reference",
            "working_papers",
            "start_date",
            "end_date",
            "current_status",
            "observations",
        )

    def render_start_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"

    def render_end_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"


class AuditTimeSummaryTable(BaseTable):
    appointment_number = tables.Column(verbose_name="Número de nombramiento")
    full_name = tables.Column(
        verbose_name="Nombre completo",
        accessor="assigned_auditor.get_full_name",
        orderable=False,
    )
    position = tables.Column(
        verbose_name="Posición",
        accessor="assigned_auditor.role",
    )
    scheduled_days = tables.Column(verbose_name="Días programados")
    worked_days = tables.Column(verbose_name="Días trabajados")
    differences = tables.Column(verbose_name="Diferencias")
    observations = tables.Column(verbose_name="Observaciones")

    class Meta(BaseTable.Meta):
        model = AuditTimeSummary
        fields = (
            "select",
            "appointment_number",
            "full_name",
            "position",
            "scheduled_days",
            "worked_days",
            "differences",
            "observations",
            "actions",
        )

    def render_scheduled_days(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"

    def render_worked_days(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"

    def render_differences(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="days")
        return "Días no disponibles"


class SummaryHoursWorkedTable(BaseTable):
    observations = tables.Column(verbose_name="Observaciones")
    differences = tables.Column(verbose_name="Diferencias")
    total_hours_worked = tables.Column(verbose_name="Total de horas trabajadas")
    total_scheduled_hours = tables.Column(verbose_name="Total de horas programadas")
    month = tables.Column(verbose_name="Mes")

    class Meta(BaseTable.Meta):
        model = SummaryHoursWorked
        fields = (
            "select",
            "month",
            "total_scheduled_hours",
            "total_hours_worked",
            "differences",
            "observations",
            "actions",
        )

    def render_total_scheduled_hours(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"

    def render_total_hours_worked(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"

    def render_differences(self, value):
        if isinstance(value, timedelta):
            return format_duration(duration=value, show_only="hours")
        return "Días no disponibles"


class WorkingPapersStatusesTable(BaseTable):
    working_papers = tables.Column(verbose_name="Papeles de Trabajo")
    observations = tables.Column(verbose_name="Observaciones")
    reference = tables.Column(verbose_name="Ref")
    start_date = tables.Column(verbose_name="Fecha de Inicio")
    end_date = tables.Column(verbose_name="Fecha de Finalización")
    current_status = tables.TemplateColumn(
        verbose_name="Estado Actual",
        template_code="""
        <span class="badge 
            {% if record.current_status.name == "inicializado" %}badge-inicializado{% elif record.current_status.name == "en proceso" %}badge-en-proceso{% elif record.current_status.name == "en revisión" %}badge-en-revision{% elif record.current_status.name == "aprobado" %}badge-aprobado{% elif record.current_status.name == "terminado" %}badge-terminado{% elif record.current_status.name == "en espera" %}badge-en-espera{% elif record.current_status.name == "rechazado" %}badge-rechazado{% elif record.current_status.name == "completado" %}badge-completado{% elif record.current_status.name == "archivado" %}badge-archivado{% elif record.current_status.name == "cancelado" %}badge-cancelado{% endif %}
        ">{{ record.current_status }}</span>
        """,
    )

    class Meta(BaseTable.Meta):
        model = WorkingPapersStatus
        fields = (
            "select",
            "reference",
            "working_papers",
            "start_date",
            "end_date",
            "current_status",
            "observations",
            "actions",
        )

    def render_start_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"

    def render_end_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"


class BaseAuditMarksTable(tables.Table):
    image = tables.TemplateColumn(
        verbose_name="Símbolo",
        template_code="""<img src='{{record.image}}' alt={{record.id}} width=35 height=35 />""",
        orderable=False,
        attrs={"td": {"class": "td-image"}},
    )
    name = tables.Column(verbose_name="Nombre de la marca")
    description = tables.Column(verbose_name="Descripción")

    class Meta(BaseTable.Meta):
        model = AuditMarks
        fields = (
            "image",
            "name",
            "description",
        )


class AuditMarksTable(BaseTable):
    image = tables.TemplateColumn(
        verbose_name="Símbolo",
        template_code="""<img src='{{record.image}}' alt={{record.id}} width=35 height=35 />""",
    )
    name = tables.Column(verbose_name="Nombre de la marca")
    description = tables.Column(verbose_name="Descripción")

    class Meta(BaseTable.Meta):
        model = AuditMarks
        fields = ("select", "image", "name", "description", "actions")


class BaseCurrencyTypesTable(tables.Table):
    country = tables.Column(verbose_name="País")
    name = tables.Column(verbose_name="Nombre")
    currency = tables.Column(verbose_name="Moneda")
    code = tables.Column(verbose_name="Código")

    class Meta(BaseTable.Meta):
        model = AuditMarks
        fields = (
            "country",
            "currency",
            "name",
            "code",
        )


class CurrencyTypesTable(BaseTable):
    country = tables.Column(verbose_name="País")
    name = tables.Column(verbose_name="Nombre")
    currency = tables.Column(verbose_name="Moneda")
    code = tables.Column(verbose_name="Código")

    class Meta(BaseTable.Meta):
        model = AuditMarks
        fields = ("select", "country", "currency", "name", "code", "actions")


class BaseActivitiesTable(tables.Table):
    activity = tables.Column(verbose_name="Actividad")
    reference = tables.Column(verbose_name="Ref.")
    appointment_number = tables.Column(verbose_name="Nombramiento No.")
    created_by = tables.Column(
        verbose_name="Responsable",
        accessor="created_by.get_full_name",
        orderable=False,
    )
    start_date = tables.Column(verbose_name="F. Inicio")
    end_date = tables.Column(verbose_name="F. Finalización")
    current_status = tables.Column(verbose_name="Edo. Actual")
    total_days = tables.Column(
        verbose_name="Días totales", accessor="get_total_days_legible"
    )
    observations = tables.Column(verbose_name="Observaciones")

    class Meta(BaseTable.Meta):
        model = Activity
        fields = (
            "activity",
            "reference",
            "appointment_number",
            "created_by",
            "start_date",
            "end_date",
            "current_status",
            "total_days",
            "observations",
        )

    def render_start_date(self, value):
        if isinstance(value, datetime):
            # Formato: día/mes/año
            return value.strftime("%d/%m/%Y")
        return "Fecha no disponible"

    def render_end_date(self, value):
        if isinstance(value, datetime):
            # Formato: día/mes/año
            return value.strftime("%d/%m/%Y")
        return "Fecha no disponible"


class ActivitiesTable(BaseTable):
    activity = tables.Column(verbose_name="Actividad")
    created_by = tables.Column(
        verbose_name="Auditor Responsable",
        accessor="created_by.get_full_name",
        orderable=False,
    )
    reference = tables.Column(verbose_name="Referencia")
    appointment_number = tables.Column(verbose_name="Nombramiento No.")
    start_date = tables.Column(verbose_name="Fecha de inicio")
    end_date = tables.Column(verbose_name="Fecha de finalización")
    current_status = tables.Column(verbose_name="Estado Actual")
    total_days = tables.Column(
        verbose_name="Días totales", accessor="get_total_days_legible"
    )
    observations = tables.Column(verbose_name="Observaciones")

    class Meta(BaseTable.Meta):
        model = Activity
        fields = (
            "select",
            "activity",
            "reference",
            "appointment_number",
            "created_by",
            "start_date",
            "end_date",
            "current_status",
            "total_days",
            "observations",
            "actions",
        )

    def render_start_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"

    def render_end_date(self, value):
        if isinstance(value, datetime):
            return formats.date_format(value, "DATE_FORMAT")
        return "Fecha no disponible"
