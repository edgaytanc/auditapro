from django import forms

from common.templatetags.filters import format_duration_only_number
from common.utils import convert_date_str_to_datetime
from tools.models import AuditTimeSummary, WorkingPapersStatus


class AuditTimeSummaryForm(forms.ModelForm):
    scheduled_days_str = forms.IntegerField(
        label="Días programados (en enteros)", required=True
    )
    worked_days_str = forms.IntegerField(
        label="Días trabajados (en enteros)", required=True
    )

    class Meta:
        model = AuditTimeSummary
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["worked_days_str"].initial = self.instance.worked_days.days
            self.fields["scheduled_days_str"].initial = (
                self.instance.scheduled_days.days
            )


class SummaryHoursWorkedForm(forms.ModelForm):
    total_hours_worked_str = forms.IntegerField(
        label="Horas trabajadas (en enteros)", required=True
    )
    total_scheduled_hours_str = forms.IntegerField(
        label="Horas programadas (en enteros)", required=True
    )

    class Meta:
        model = AuditTimeSummary
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["total_hours_worked_str"].initial = int(
                format_duration_only_number(self.instance.total_hours_worked, "hours")
            )
            self.fields["total_scheduled_hours_str"].initial = int(
                format_duration_only_number(
                    self.instance.total_scheduled_hours, "hours"
                )
            )


class WorkingPapersStatusesForm(forms.ModelForm):
    start_date_str = forms.DateField(
        label="Fecha de inicio",
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    end_date_str = forms.DateField(
        label="Fecha de finalización (esta tiene que ser después de la de inicio)",
        required=True,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    class Meta:
        model = WorkingPapersStatus
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                self.fields["start_date_str"].initial = (
                    self.instance.start_date.strftime("%Y-%m-%d")
                )
            if self.instance.end_date:
                self.fields["end_date_str"].initial = self.instance.end_date.strftime(
                    "%Y-%m-%d"
                )
