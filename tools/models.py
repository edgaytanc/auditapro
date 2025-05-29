from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.utils import formats
from common.templatetags.filters import format_duration
from tools.errors import (
    StartDateAfterEndDateError,
    TotalWorkedDaysHigherThanScheduledDaysError,
    TotalWorkedHoursHigherThanScheduledHoursError,
)
import calendar
from django.contrib.auth import get_user_model
from audits.models import Audit
from tools.utils import get_and_year_months_between_dates
from users.errors import UserUnauthorized
from django.core.validators import MinValueValidator, MaxValueValidator
from functools import reduce
from django.utils import translation

User = get_user_model()


class CurrentStatus(models.Model):
    name = models.CharField(max_length=255)
    verbose_name = models.CharField(max_length=255)

    def __str__(self):
        return self.verbose_name


class Months(models.Model):
    name = models.CharField(max_length=255, unique=True)
    days = models.IntegerField(
        validators=[MinValueValidator(28), MaxValueValidator(31)]
    )

    def __str__(self):
        return self.name.capitalize()


class WorkingPapersStatus(models.Model):
    auditor = models.ForeignKey(
        User, related_name="working_papers_auditor", on_delete=models.CASCADE
    )
    audit = models.ForeignKey(
        Audit, related_name="working_papers_audit", on_delete=models.CASCADE
    )
    reference = models.CharField(max_length=255, blank=True, default=None, null=True)
    working_papers = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    current_status = models.ForeignKey(
        CurrentStatus,
        related_name="working_papers_statuscurrent_status",
        on_delete=models.CASCADE,
    )
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def check_if_audit_is_assigned_to_auditor(self):
        if (
            self.auditor.role == "audit_manager"
            and self.audit.audit_manager != self.auditor
        ):
            raise UserUnauthorized()

        if (
            self.auditor.role == "supervisor" or self.auditor.role == "auditor"
        ) and not self.audit.assigned_users.filter(id=self.auditor.pk).exists():
            raise UserUnauthorized()

    def save(self, *args, **kwargs):
        self.check_if_audit_is_assigned_to_auditor()
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise StartDateAfterEndDateError()
        self.updated_at = timezone.now()

        if not self.reference:
            self.reference = (
                f"Nom-{int(self.audit.pk):02}"
                if int(self.audit.pk) < 10
                else f"Nom-{self.audit.pk}"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.working_papers} - {self.current_status}"

    def formatted_start_date(self):
        return formats.date_format(self.start_date, "DATE_FORMAT")

    def formatted_end_date(self):
        return formats.date_format(self.end_date, "DATE_FORMAT")


class SummaryHoursWorked(models.Model):
    auditor = models.ForeignKey(
        User, related_name="summary_hours_auditor", on_delete=models.CASCADE
    )
    audit = models.ForeignKey(
        Audit, related_name="summary_hours_audit", on_delete=models.CASCADE
    )
    month = models.ForeignKey(
        Months, related_name="summary_hours_month", on_delete=models.CASCADE
    )
    total_scheduled_hours = models.DurationField()
    total_hours_worked = models.DurationField()
    differences = models.DurationField(null=True, blank=True)
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Resumen de horas trabajadas de: {self.audit} del mes {self.month}"

    def check_if_audit_is_assigned_to_auditor(self):
        if (
            self.auditor.role == "audit_manager"
            and self.audit.audit_manager != self.auditor
        ):
            raise UserUnauthorized()

        if (
            self.auditor.role == "supervisor" or self.auditor.role == "auditor"
        ) and not self.audit.assigned_users.filter(id=self.auditor.pk).exists():
            raise UserUnauthorized()

    def save(self, *args, **kwargs):
        self.check_if_audit_is_assigned_to_auditor()
        if self.total_hours_worked > self.total_scheduled_hours:
            raise TotalWorkedHoursHigherThanScheduledHoursError()
        self.differences = self.total_scheduled_hours - self.total_hours_worked
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class AuditTimeSummary(models.Model):
    auditor = models.ForeignKey(
        User, related_name="audit_time_summary_auditor", on_delete=models.CASCADE
    )
    audit = models.ForeignKey(
        Audit, related_name="audit_time_summary_audit", on_delete=models.CASCADE
    )
    appointment_number = models.CharField(max_length=255)
    scheduled_days = models.DurationField()
    worked_days = models.DurationField()
    differences = models.DurationField(null=True, blank=True)
    observations = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    assigned_auditor = models.ForeignKey(
        User,
        related_name="audit_time_summary_assigned_auditor",
        on_delete=models.CASCADE,
    )

    def __str__(self) -> str:
        return (
            f"Resumen de tiempo de Auditoría - Nombramiento: {self.appointment_number}"
        )

    def check_if_audit_is_assigned_to_auditor(self):
        if (
            self.auditor.role == "audit_manager"
            and self.audit.audit_manager != self.auditor
        ):
            raise UserUnauthorized()

        if (
            self.auditor.role == "supervisor" or self.auditor.role == "auditor"
        ) and not self.audit.assigned_users.filter(id=self.auditor.pk).exists():
            raise UserUnauthorized()

    def save(self, *args, **kwargs):
        self.check_if_audit_is_assigned_to_auditor()
        if self.worked_days > self.scheduled_days:
            raise TotalWorkedDaysHigherThanScheduledDaysError()

        self.differences = self.scheduled_days - self.worked_days
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)


class AuditMarks(models.Model):
    image = models.CharField(max_length=255)
    description = models.TextField()
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=255)
    verbose_name = models.CharField(max_length=255, blank=True, null=True)
    alpha2_code = models.CharField(max_length=2, unique=True)
    alpha3_code = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.verbose_name or self.name


class CurrencyType(models.Model):
    country = models.ForeignKey(
        "Country", on_delete=models.CASCADE, related_name="currencies"
    )
    name = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=10)
    code = models.CharField(max_length=4, unique=True, default="")

    def __str__(self):
        return f"{self.country} ({self.name}) - {self.currency}"


class ActivityTotalDaysPerMonth(models.Model):
    total_days = models.DurationField(editable=False, default=timedelta())

    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()

    activity = models.ForeignKey(
        "Activity",
        related_name="activity_total_days_per_month_activity",
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        if not (1 <= self.month <= 12):
            raise ValueError("El valor de 'month' debe estar entre 1 y 12.")

        activity_total_days_per_month_yet = (
            ActivityTotalDaysPerMonth.objects.filter(
                month=self.month, year=self.year, activity=self.activity
            )
            .exclude(pk=self.pk)
            .first()
        )

        if activity_total_days_per_month_yet:
            raise ValueError(
                "Ya existe una instancia para la misma actividad, mes y año."
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.activity} - {self.year}/{self.month} - {self.total_days}"


class Activity(models.Model):
    created_by = models.ForeignKey(
        User, related_name="created_by", on_delete=models.CASCADE
    )
    audit = models.ForeignKey(
        Audit, related_name="activity_audit", on_delete=models.CASCADE
    )
    activity = models.CharField(max_length=255)
    reference = models.CharField(max_length=255, blank=True, default=None, null=True)
    appointment_number = models.CharField(max_length=255)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    current_status = models.ForeignKey(
        CurrentStatus,
        related_name="activity_current_status",
        on_delete=models.CASCADE,
    )

    observations = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.activity} - {self.appointment_number} | {self.audit}"

    def get_activity_total_days_per_month_list_dict(self):
        with translation.override("es"):
            return [
                {
                    "month": activity_total_days_per_month.month,
                    "month_name": calendar.month_name[
                        activity_total_days_per_month.month
                    ],
                    "year": activity_total_days_per_month.year,
                    "total_days": activity_total_days_per_month.total_days,
                }
                for activity_total_days_per_month in ActivityTotalDaysPerMonth.objects.filter(
                    activity=self
                )
            ]

    def get_valid_years_and_months(self):
        months, years = get_and_year_months_between_dates(
            self.start_date, self.end_date
        )
        return months, years

    def __create_activity_total_days_per_month_instances(self):
        months, years = self.get_valid_years_and_months()
        for month, year in zip(months, years):
            if ActivityTotalDaysPerMonth.objects.filter(
                activity=self,
                month=month,
                year=year,
            ).exists():
                continue

            ActivityTotalDaysPerMonth.objects.create(
                activity=self, month=month, year=year, total_days=timedelta()
            )

    def __check_activity_total_days_per_month_instances(self):
        activity_total_days_per_month_instances = (
            ActivityTotalDaysPerMonth.objects.filter(activity=self)
        )
        months, years = self.get_valid_years_and_months()
        for activity_total_days_per_month in activity_total_days_per_month_instances:
            if (
                activity_total_days_per_month.month not in months
                or activity_total_days_per_month.year not in years
            ):
                activity_total_days_per_month.delete()
                continue

    def save(self, *args, **kwargs):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise StartDateAfterEndDateError()
        # if self.created_by != self.audit.audit_manager:
        #     raise UserUnauthorized()
        # if self.created_by.role.name != "auditor":
        #     raise UserUnauthorized("Solo Uditores pueden crear actividades")
        if not self.reference:
            self.reference = (
                f"Nom-{int(self.audit.pk):02}"
                if int(self.audit.pk) < 10
                else f"Nom-{self.audit.pk}"
            )

        super().save(*args, **kwargs)

        self.__create_activity_total_days_per_month_instances()
        self.__check_activity_total_days_per_month_instances()

    def get_total_days(self):
        return reduce(
            lambda acc, activity_p_m: activity_p_m.total_days + acc,
            list(ActivityTotalDaysPerMonth.objects.filter(activity=self)),
            timedelta(),
        )

    def get_total_days_legible(self):
        return format_duration(duration=self.get_total_days(), show_only="days")
