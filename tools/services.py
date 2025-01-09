import calendar
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from audits.errors import AuditDoNotExits, NullAuditError
from audits.models import Audit
from common.templatetags.filters import format_duration_field
from users.errors import (
    AuditorInvalidError,
    AuditorNullError,
    UserDoNotExits,
    UserUnauthorized,
)
from .errors import (
    AuditTimeSummaryDoesNotExitsError,
    CurrencyCountryAlredyAssignedError,
    InvalidEndDateError,
    InvalidStartDateError,
    InvalidTotalDaysError,
    InvalidYearError,
    MonthDoesNotExitsError,
    NullMonthError,
    NullNameError,
    NullScheduledDaysError,
    NullWorkedDaysError,
    InvalidScheduledDaysError,
    InvalidWorkedDaysError,
    NullAppointmentNumberError,
    InvalidAppointmentNumberError,
    NullCurrentStatusError,
    NullEndDateError,
    NullReferenceError,
    NullStartDateError,
    NullWorkinPapersError,
    CurrentStatusDoesNotExitsError,
    InvalidCurrentStatusError,
    StartDateAfterEndDateError,
    TotalWorkedDaysHigherThanScheduledDaysError,
    TotalWorkedHoursHigherThanScheduledHoursError,
    WorkingPapersStatusDoesNotExitsError,
    SummaryHoursWorkedDoesNotExitsError,
    NullScheduledHoursError,
    NullWorkedHoursError,
    InvalidMonthError,
    InvalidScheduledHoursError,
    InvalidWorkedHoursError,
    AuditMarkWithThatDescriptionAlredyExits,
    AuditMarkWithThatImageAlredyExits,
    AuditMarkWithThatNameAlredyExits,
    NullDescriptionAuditMarkError,
    NullImageAuditMarkError,
    NullNameAuditMarkError,
    CurrencyCodeAlredyAssignedError,
    CurrencyNameAlredyAssignedError,
    InvalidCountryError,
    InvalidCurrencyCodeError,
    InvalidCurrencyNameError,
    InvalidCurrencyCurrencyError,
)
from .models import (
    Activity,
    ActivityTotalDaysPerMonth,
    AuditMarks,
    AuditTimeSummary,
    Country,
    CurrencyType,
    WorkingPapersStatus,
    SummaryHoursWorked,
    CurrentStatus,
    Months,
)
from common.utils import convert_date_str_to_datetime, is_valid_date
from audits.types import Audit as AuditType, is_audit_type
from django.contrib.auth import get_user_model

User = get_user_model()


def create_audit_time_summary(
    req: HttpRequest,
    audit: AuditType,
    appointment_number: str,
    scheduled_days: str,
    worked_days: str,
    observations: str,
    assigned_auditor: str,
):
    try:
        if not req:
            raise UserUnauthorized()
        if not isinstance(req, HttpRequest):
            raise UserUnauthorized()
        if not req.user:
            raise UserUnauthorized()
        user_id = req.user.id
        if not user_id:
            raise UserUnauthorized()
        if not assigned_auditor:
            raise AuditorNullError()
        if not assigned_auditor.isdigit():
            raise AuditorInvalidError()
        if not audit:
            raise NullAuditError()
        if not is_audit_type(audit=audit):
            raise AuditDoNotExits()
        if not appointment_number:
            raise NullAppointmentNumberError()
        if not scheduled_days:
            raise NullScheduledDaysError()
        if not appointment_number.isdigit():
            raise InvalidAppointmentNumberError()
        if not scheduled_days.isdigit():
            raise InvalidScheduledDaysError()
        if worked_days is None:
            raise NullWorkedDaysError()
        if not worked_days.isdigit() or int(worked_days) < 0:
            raise InvalidWorkedDaysError()

        audit_to_assing = Audit.objects.get(pk=int(audit["id"]))

        if not audit_to_assing:
            raise UserUnauthorized()
        user_role = req.user.role.name

        if not user_role:
            raise UserUnauthorized()

        if user_role == "audit_manager" and audit_to_assing.audit_manager != req.user:
            raise UserUnauthorized()

        if (
            user_role == "supervisor" or user_role == "auditor"
        ) and not audit_to_assing.assigned_users.filter(id=user_id).exists():
            raise UserUnauthorized()

        assigned_auditor_instance = get_object_or_404(
            User,
            pk=int(assigned_auditor),
        )

        if not audit_to_assing.assigned_users.filter(
            pk=assigned_auditor_instance.pk
        ).exists():
            raise UserDoNotExits()

        scheduled_days_duration = format_duration_field(int(scheduled_days), "days")
        worked_days_duration = format_duration_field(int(worked_days), "days")

        new_audit_time_summary = AuditTimeSummary.objects.create(
            audit=audit_to_assing,
            auditor=req.user,
            appointment_number=int(appointment_number),
            assigned_auditor=assigned_auditor_instance,
            scheduled_days=scheduled_days_duration,
            worked_days=worked_days_duration,
            observations=observations if observations else None,
        )

        new_audit_time_summary.save()
    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except Exception as e:
        raise e


def delete_audit_time_summary(audit_summary_time_to_delete: AuditTimeSummary):
    try:
        audit_summary_time_to_delete.delete()
    except AuditTimeSummary.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def create_status_of_work_papers(
    req: HttpRequest,
    audit: AuditType,
    working_papers: str,
    start_date: str,
    end_date: str,
    current_status: str,
    observations: str,
):
    try:
        if not req:
            raise UserUnauthorized()
        if not isinstance(req, HttpRequest):
            raise UserUnauthorized()
        if not req.user:
            raise UserUnauthorized()
        user_id = req.user.id

        if not user_id:
            raise UserUnauthorized()
        if not audit:
            raise NullAuditError()
        if not is_audit_type(audit=audit):
            raise AuditDoNotExits()
        if not working_papers:
            raise NullWorkinPapersError()
        if not start_date:
            raise NullStartDateError()
        if not end_date:
            raise NullEndDateError()
        if not current_status:
            raise NullCurrentStatusError()
        if not current_status.isdigit():
            raise InvalidCurrentStatusError()

        if not is_valid_date(start_date):
            raise InvalidStartDateError()

        if not is_valid_date(end_date):
            raise InvalidEndDateError()

        current_status_instance = CurrentStatus.objects.get(id=current_status)

        if not current_status_instance:
            raise CurrentStatusDoesNotExitsError()

        audit_to_assing = Audit.objects.get(pk=int(audit["id"]))

        if not audit_to_assing:
            raise UserUnauthorized()

        user_role = req.user.role.name

        if not user_role:
            raise UserUnauthorized()
        if user_role == "audit_manager" and audit_to_assing.audit_manager != req.user:
            raise UserUnauthorized()

        if (
            user_role == "supervisor" or user_role == "auditor"
        ) and not audit_to_assing.assigned_users.filter(id=user_id).exists():
            raise UserUnauthorized()

        start_date_date_time = convert_date_str_to_datetime(start_date)

        end_date_date_time = convert_date_str_to_datetime(end_date)

        new_status_of_work_papers = WorkingPapersStatus.objects.create(
            auditor=req.user,
            audit=audit_to_assing,
            working_papers=working_papers,
            start_date=start_date_date_time,
            end_date=end_date_date_time,
            current_status=current_status_instance,
            observations=observations if observations else None,
        )

        new_status_of_work_papers.save()
    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except CurrentStatus.DoesNotExist:
        raise CurrentStatusDoesNotExitsError()
    except Exception as e:
        raise e


def delete_status_of_work_papers(
    status_of_work_papers_to_delete: WorkingPapersStatus,
):
    try:
        status_of_work_papers_to_delete.delete()
    except WorkingPapersStatus.DoesNotExist:
        raise WorkingPapersStatusDoesNotExitsError()
    except Exception as e:
        raise e


def delete_summary_hours_worked(summary_hours_worked_to_delete):
    try:
        summary_hours_worked_to_delete.delete()
    except SummaryHoursWorked.DoesNotExist:
        raise SummaryHoursWorkedDoesNotExitsError()
    except Exception as e:
        raise e


def create_summary_hours_worked(
    req: HttpRequest,
    audit: AuditType,
    month: str,
    total_scheduled_hours: str,
    total_worked_hours: str,
    observations: str,
):
    try:
        if not req:
            raise UserUnauthorized()
        if not isinstance(req, HttpRequest):
            raise UserUnauthorized()
        if not req.user:
            raise UserUnauthorized()
        user_id = req.user.id
        if not user_id:
            raise UserUnauthorized()
        if not audit:
            raise NullAuditError()
        if not is_audit_type(audit=audit):
            raise AuditDoNotExits()
        if not month:
            raise NullMonthError()
        if not total_scheduled_hours:
            raise NullScheduledHoursError()
        if not total_scheduled_hours.isdigit():
            raise InvalidScheduledHoursError()
        if total_worked_hours is None:
            raise NullWorkedHoursError()
        if not total_worked_hours.isdigit() or int(total_worked_hours) < 0:
            raise InvalidWorkedHoursError()
        if not month.isdigit():
            raise InvalidMonthError()
        if int(total_worked_hours) > int(total_scheduled_hours):
            raise TotalWorkedHoursHigherThanScheduledHoursError()
        month_instance = Months.objects.get(id=month)

        if not month_instance:
            raise MonthDoesNotExitsError()

        audit_to_assing = Audit.objects.get(pk=int(audit["id"]))

        if not audit_to_assing:
            raise UserUnauthorized()
        user_role = req.user.role.name

        if not user_role:
            raise UserUnauthorized()
        if user_role == "audit_manager" and audit_to_assing.audit_manager != req.user:
            raise UserUnauthorized()

        if (
            user_role == "supervisor" or user_role == "auditor"
        ) and not audit_to_assing.assigned_users.filter(id=user_id).exists():
            raise UserUnauthorized()

        scheduled_hours_duration = format_duration_field(
            int(total_scheduled_hours), "hours"
        )
        worked_hours_duration = format_duration_field(int(total_worked_hours), "hours")

        new_summary_hours_worked = SummaryHoursWorked.objects.create(
            auditor=req.user,
            audit=audit_to_assing,
            month=month_instance,
            total_scheduled_hours=scheduled_hours_duration,
            total_hours_worked=worked_hours_duration,
            observations=observations if observations else None,
        )

        new_summary_hours_worked.save()

    except Audit.DoesNotExist:
        raise AuditDoNotExits()
    except Months.DoesNotExist:
        raise MonthDoesNotExitsError()
    except Exception as e:
        raise e


def update_audit_time_summary(
    audit_time_summary_to_update: AuditTimeSummary,
    appointment_number: str,
    scheduled_days: str,
    worked_days: str,
    observations: str,
):
    try:
        if not appointment_number:
            raise NullAppointmentNumberError()
        if not scheduled_days:
            raise NullScheduledDaysError()
        if not appointment_number.isdigit():
            raise InvalidAppointmentNumberError()
        if not scheduled_days.isdigit():
            raise InvalidScheduledDaysError()
        if worked_days is None:
            raise NullWorkedDaysError()
        if not worked_days.isdigit() or int(worked_days) < 0:
            raise InvalidWorkedDaysError()

        if int(worked_days) > int(scheduled_days):
            raise TotalWorkedDaysHigherThanScheduledDaysError()

        scheduled_days_duration = format_duration_field(int(scheduled_days), "days")
        worked_days_duration = format_duration_field(int(worked_days), "days")
        audit_time_summary_to_update.appointment_number = int(appointment_number)
        audit_time_summary_to_update.scheduled_days = scheduled_days_duration
        audit_time_summary_to_update.worked_days = worked_days_duration
        audit_time_summary_to_update.observations = observations
        audit_time_summary_to_update.save()

    except AuditTimeSummary.DoesNotExist:
        raise AuditTimeSummaryDoesNotExitsError()
    except Exception as e:
        raise e


def update_summary_hours_worked(
    summary_hours_worked_to_update: SummaryHoursWorked,
    month: str,
    total_scheduled_hours: str,
    total_hours_worked: str,
    observations: str | None,
):
    try:
        if not month:
            raise NullMonthError()

        if not total_scheduled_hours:
            raise NullScheduledHoursError()
        if total_hours_worked is None:
            raise NullWorkedHoursError()
        if not total_hours_worked.isdigit() or int(total_hours_worked) < 0:
            raise InvalidWorkedHoursError()
        if not month.isdigit():
            raise InvalidMonthError()

        if not total_hours_worked.isdigit():
            raise InvalidWorkedHoursError()
        if not total_scheduled_hours.isdigit():
            raise InvalidScheduledHoursError()

        if int(total_hours_worked) > int(total_scheduled_hours):
            raise TotalWorkedHoursHigherThanScheduledHoursError()

        month_instance = Months.objects.get(id=int(month)) if month else None

        if not month_instance:
            raise MonthDoesNotExitsError()

        total_scheduled_hours_duration = format_duration_field(
            int(total_scheduled_hours), "hours"
        )

        total_worked_hours_duration = format_duration_field(
            int(total_hours_worked), "hours"
        )

        summary_hours_worked_to_update.month = month_instance
        summary_hours_worked_to_update.total_hours_worked = total_worked_hours_duration
        summary_hours_worked_to_update.total_scheduled_hours = (
            total_scheduled_hours_duration
        )
        summary_hours_worked_to_update.observations = (
            observations if observations else None
        )

        summary_hours_worked_to_update.save()
    except SummaryHoursWorked.DoesNotExist:
        raise SummaryHoursWorkedDoesNotExitsError()
    except Months.DoesNotExist:
        raise MonthDoesNotExitsError()
    except Exception as e:
        raise e


def update_status_of_work_papers(
    status_of_work_papers_to_update: WorkingPapersStatus,
    current_status: str,
    end_date: str,
    start_date: str,
    working_papers: str,
    reference: str,
    observations: str | None,
):
    try:
        if not current_status:
            raise NullCurrentStatusError()
        if not current_status.isdigit():
            raise InvalidCurrentStatusError()
        if not end_date:
            raise NullEndDateError()
        if not start_date:
            raise NullStartDateError()
        if not working_papers:
            raise NullWorkinPapersError()

        if not is_valid_date(start_date):
            raise InvalidStartDateError()

        if not is_valid_date(end_date):
            raise InvalidEndDateError()

        if not reference:
            raise NullReferenceError()

        current_status_instance = CurrentStatus.objects.get(id=current_status)

        if not current_status_instance:
            raise CurrentStatusDoesNotExitsError()

        start_convert_date = convert_date_str_to_datetime(start_date)
        end_convert_date = convert_date_str_to_datetime(end_date)

        if start_convert_date >= end_convert_date:
            raise StartDateAfterEndDateError()

        if (
            reference == status_of_work_papers_to_update.reference
            and working_papers == status_of_work_papers_to_update.working_papers
            and start_convert_date == status_of_work_papers_to_update.start_date
            and end_convert_date == status_of_work_papers_to_update.end_date
            and current_status_instance.pk
            == status_of_work_papers_to_update.current_status.pk
            and observations == status_of_work_papers_to_update.observations
        ):
            return

        status_of_work_papers_to_update.reference = reference
        status_of_work_papers_to_update.working_papers = working_papers
        status_of_work_papers_to_update.start_date = start_convert_date
        status_of_work_papers_to_update.end_date = end_convert_date
        status_of_work_papers_to_update.current_status = current_status_instance
        status_of_work_papers_to_update.observations = (
            observations if observations else None
        )

        status_of_work_papers_to_update.save()

    except WorkingPapersStatus.DoesNotExist:
        raise WorkingPapersStatusDoesNotExitsError()
    except CurrentStatus.DoesNotExist:
        raise CurrentStatusDoesNotExitsError()
    except Exception as e:
        raise e


def create_audit_mark(name: str, description: str, image: str):
    try:
        if not name:
            raise NullNameAuditMarkError()
        if not description:
            raise NullDescriptionAuditMarkError()
        if not image:
            raise NullImageAuditMarkError()

        if AuditMarks.objects.filter(name=name).exists():
            raise AuditMarkWithThatNameAlredyExits()

        if AuditMarks.objects.filter(description=description).exists():
            raise AuditMarkWithThatDescriptionAlredyExits()
        if AuditMarks.objects.filter(image=image).exists():
            raise AuditMarkWithThatImageAlredyExits()

        new_audit_mark = AuditMarks.objects.create(
            name=name, description=description, image=image
        )
        new_audit_mark.save()
    except Exception as e:
        raise e


def update_audit_mark(
    audit_mark_to_update: AuditMarks, name: str, description: str, image: str
):
    try:
        if not name:
            raise NullNameAuditMarkError()
        if not description:
            raise NullDescriptionAuditMarkError()
        if not image:
            raise NullImageAuditMarkError()

        if (
            AuditMarks.objects.filter(name=name).exists()
            and audit_mark_to_update.name != name
        ):
            raise AuditMarkWithThatNameAlredyExits()

        if (
            AuditMarks.objects.filter(description=description).exists()
            and audit_mark_to_update.description != description
        ):
            raise AuditMarkWithThatDescriptionAlredyExits()
        if (
            AuditMarks.objects.filter(image=image).exists()
            and audit_mark_to_update.image != image
        ):
            raise AuditMarkWithThatImageAlredyExits()

        audit_mark_to_update.name = name
        audit_mark_to_update.description = description
        audit_mark_to_update.image = image

        audit_mark_to_update.save()
    except Exception as e:
        raise e


def delete_audit_mark(audit_mark_to_delete: AuditMarks):
    try:
        audit_mark_to_delete.delete()
    except AuditMarks.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def create_currency_type(name: str, currency: str, code: str, country_id: str):
    try:
        if not name:
            raise InvalidCurrencyNameError()
        if not currency:
            raise InvalidCurrencyCurrencyError()
        if not country_id:
            raise InvalidCountryError()
        if not code:
            raise InvalidCurrencyCodeError()

        if CurrencyType.objects.filter(name=name).exists():
            raise CurrencyNameAlredyAssignedError()

        if CurrencyType.objects.filter(code=code).exists():
            raise CurrencyCodeAlredyAssignedError()

        country_to_assign = Country.objects.get(pk=country_id)
        if not country_to_assign:
            raise InvalidCountryError()

        if CurrencyType.objects.filter(country=country_to_assign).exists():
            raise CurrencyCountryAlredyAssignedError()

        new_currency_type = CurrencyType.objects.create(
            name=name, currency=currency, country=country_to_assign, code=code
        )
        new_currency_type.save()
    except Country.DoesNotExist:
        raise InvalidCountryError()
    except Exception as e:
        raise e


def update_currency_type(
    currency_type_to_update: CurrencyType,
    name: str,
    currency: str,
    code: str,
    country_id: str,
):
    try:
        if not name:
            raise InvalidCurrencyNameError()
        if not currency:
            raise InvalidCurrencyCurrencyError()
        if not country_id:
            raise InvalidCountryError()
        if not code:
            raise InvalidCurrencyCodeError()

        if (
            CurrencyType.objects.filter(name=name).exists()
            and currency_type_to_update.name != name
        ):
            raise CurrencyNameAlredyAssignedError()

        if (
            CurrencyType.objects.filter(code=code).exists()
            and currency_type_to_update.code != code
        ):
            raise CurrencyCodeAlredyAssignedError()

        country_to_assign = Country.objects.get(pk=country_id)
        if not country_to_assign:
            raise InvalidCountryError()

        if (
            CurrencyType.objects.filter(country=country_to_assign).exists()
            and currency_type_to_update.country != country_to_assign
        ):
            raise CurrencyCountryAlredyAssignedError()

        if currency_type_to_update.name != name:
            currency_type_to_update.name = name

        if currency_type_to_update.currency != currency:
            currency_type_to_update.currency = currency

        if currency_type_to_update.code != code:
            currency_type_to_update.code = code

        if currency_type_to_update.country != country_to_assign:
            currency_type_to_update.country = country_to_assign
        currency_type_to_update.save()
    except Country.DoesNotExist:
        raise InvalidCountryError()
    except Exception as e:
        raise e


def delete_currency_type(currency_type_to_delete: CurrencyType):
    try:
        currency_type_to_delete.delete()
    except CurrencyType.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def create_activity(
    req: HttpRequest,
    audit: AuditType,
    end_date: str,
    start_date: str,
    activity: str,
    current_status_id: str,
    appointment_number: str,
    observations: str | None = None,
):
    try:
        if not req:
            raise UserUnauthorized()

        if not isinstance(req, HttpRequest):
            raise UserUnauthorized()

        if not audit:
            raise NullAuditError()

        if not is_audit_type(audit=audit):
            raise AuditDoNotExits()

        if not end_date:
            raise InvalidEndDateError()

        if not is_valid_date(end_date):
            raise InvalidEndDateError()

        if not start_date:
            raise InvalidStartDateError()

        if not is_valid_date(start_date):
            raise InvalidStartDateError()

        if not activity:
            raise NullNameError()

        if not appointment_number:
            raise NullAppointmentNumberError()

        if not current_status_id:
            raise InvalidCurrentStatusError()

        if not current_status_id.isdigit():
            raise InvalidCurrentStatusError()

        if req.user.role.name != "auditor":
            raise UserUnauthorized()

        audit_to_assign = Audit.objects.get(pk=audit.get("id"))

        if not audit_to_assign:
            raise UserUnauthorized()

        # if req.user != audit_to_assign.audit_manager:
        #     raise UserUnauthorized()

        current_status_to_assign = CurrentStatus.objects.get(pk=current_status_id)
        if not current_status_to_assign:
            raise UserUnauthorized()

        start_convert_date = convert_date_str_to_datetime(start_date)
        end_convert_date = convert_date_str_to_datetime(end_date)

        Activity.objects.create(
            created_by=req.user,
            audit=audit_to_assign,
            end_date=end_convert_date,
            start_date=start_convert_date,
            activity=activity,
            current_status=current_status_to_assign,
            appointment_number=appointment_number,
            observations=observations if observations else None,
        )
    except Audit.DoesNotExist:
        raise UserUnauthorized()
    except CurrentStatus.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def update_activity(
    activity_to_update: Activity,
    end_date: str,
    start_date: str,
    activity: str,
    appointment_number: str,
    current_status_id: str,
    observations: str,
):
    try:
        if not end_date:
            raise InvalidEndDateError()

        if not is_valid_date(end_date):
            raise InvalidEndDateError()

        if not start_date:
            raise InvalidStartDateError()

        if not is_valid_date(start_date):
            raise InvalidStartDateError()

        if not activity:
            raise NullNameError()

        if not appointment_number:
            raise NullAppointmentNumberError()

        if not current_status_id:
            raise InvalidCurrentStatusError()

        if not current_status_id.isdigit():
            raise InvalidCurrentStatusError()

        current_status_to_assign = CurrentStatus.objects.get(pk=current_status_id)
        if not current_status_to_assign:
            raise UserUnauthorized()

        start_convert_date = convert_date_str_to_datetime(start_date)
        end_convert_date = convert_date_str_to_datetime(end_date)

        if start_convert_date >= end_convert_date:
            raise StartDateAfterEndDateError()

        updated = False

        if activity_to_update.activity != activity:
            activity_to_update.activity = activity
            updated = True

        if activity_to_update.appointment_number != appointment_number:
            activity_to_update.appointment_number = appointment_number
            updated = True

        if activity_to_update.start_date != start_convert_date:
            activity_to_update.start_date = start_convert_date
            updated = True

        if activity_to_update.end_date != end_convert_date:
            activity_to_update.end_date = end_convert_date
            updated = True

        if activity_to_update.current_status != current_status_to_assign:
            activity_to_update.current_status = current_status_to_assign
            updated = True

        if observations is not None and activity_to_update.observations != observations:
            activity_to_update.observations = observations
            updated = True

        if updated:
            activity_to_update.save()

    except Months.DoesNotExist:
        raise UserUnauthorized()
    except Audit.DoesNotExist:
        raise UserUnauthorized()
    except CurrentStatus.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def delete_activity(activity_to_delete: Activity):
    try:
        activity_to_delete.delete()
    except Activity.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def update_activity_total_worked_days(
    activity_to_update: Activity, month_id: str, year_id: str, total_days: str
):
    try:
        if not month_id:
            raise InvalidMonthError()

        if not year_id:
            raise InvalidYearError()

        if not month_id.isdigit():
            raise InvalidMonthError()

        if not year_id.isdigit():
            raise InvalidYearError()

        months, years = activity_to_update.get_valid_years_and_months()

        if int(month_id) not in months:
            raise InvalidMonthError()

        if int(year_id) not in years:
            raise InvalidYearError()

        if not total_days.isdigit():
            raise InvalidTotalDaysError()

        if int(total_days) < 0 and int(total_days) > 31:
            raise InvalidTotalDaysError()

        _, num_days = calendar.monthrange(int(year_id), int(month_id))

        if int(total_days) > num_days:
            raise InvalidTotalDaysError()

        # Verifica si ya existe el objeto con los parámetros de mes, año y actividad
        activity_total_days_per_month_to_update = (
            ActivityTotalDaysPerMonth.objects.filter(
                month=int(month_id), year=int(year_id), activity=activity_to_update
            ).first()
        )

        total_days_converted = format_duration_field(
            duration=int(total_days), duration_type="days"
        )

        if not activity_total_days_per_month_to_update and int(total_days) == 0:
            return

        if not activity_total_days_per_month_to_update:
            ActivityTotalDaysPerMonth.objects.create(
                month=int(month_id),
                activity=activity_to_update,
                total_days=total_days_converted,
                year=int(year_id),
            )
            return

        if activity_total_days_per_month_to_update.total_days != total_days_converted:
            activity_total_days_per_month_to_update.total_days = total_days_converted
            activity_total_days_per_month_to_update.save()

    except ActivityTotalDaysPerMonth.DoesNotExist:
        raise UserUnauthorized()
    except Exception as e:
        raise e


def get_working_papers_time_line_dic(s: str):
    return [
        {
            "status": status.name,
            "value": (
                True
                if s == status.name
                else (
                    True
                    if s == "en proceso" and status.name == "inicializado"
                    else (
                        True
                        if s == "en revisión"
                        and status.name in ("inicializado", "en proceso")
                        else (
                            True
                            if s == "aprobado"
                            and status.name
                            in ("inicializado", "en proceso", "en revisión")
                            else (
                                True
                                if s == "terminado"
                                and status.name
                                in (
                                    "inicializado",
                                    "en proceso",
                                    "en revisión",
                                    "aprobado",
                                )
                                else (
                                    True
                                    if s == "en espera"
                                    and status.name
                                    in (
                                        "inicializado",
                                        "en proceso",
                                        "en revisión",
                                        "aprobado",
                                        "terminado",
                                    )
                                    else (
                                        True
                                        if s == "rechazado"
                                        and status.name
                                        in (
                                            "inicializado",
                                            "en proceso",
                                            "en revisión",
                                            "aprobado",
                                            "terminado",
                                            "en espera",
                                        )
                                        else (
                                            True
                                            if s == "completado"
                                            and status.name
                                            in (
                                                "inicializado",
                                                "en proceso",
                                                "en revisión",
                                                "aprobado",
                                                "terminado",
                                                "en espera",
                                            )
                                            else (
                                                True
                                                if s == "archivado"
                                                and status.name
                                                in (
                                                    "inicializado",
                                                    "en proceso",
                                                    "en revisión",
                                                    "aprobado",
                                                    "terminado",
                                                    "en espera",
                                                )
                                                else (
                                                    True
                                                    if s == "cancelado"
                                                    and status.name
                                                    in (
                                                        "inicializado",
                                                        "en proceso",
                                                        "en revisión",
                                                        "aprobado",
                                                        "terminado",
                                                        "en espera",
                                                    )
                                                    else False
                                                )
                                            )
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            ),
        }
        for status in CurrentStatus.objects.all()
    ]
