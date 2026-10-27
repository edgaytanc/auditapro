import os
import calendar

from datetime import date, datetime, time, timedelta

from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.http import (
    require_POST,
)
from tools.access import (
    get_selected_audit_for_user_or_404,
    get_tool_record_for_user_or_404,
)
from tools.workpaper_catalog import (
    WORKPAPER_CATALOG,
    WORKPAPER_STATUS_DEFINITIONS,
    get_workpaper_phase,
)

User = get_user_model()

def _duration_to_unit(duration, unit="hours"):
    """
    Convierte un timedelta a horas o días decimales.
    """
    if not duration:
        return 0

    divisor = (
        86400
        if unit == "days"
        else 3600
    )

    value = duration.total_seconds() / divisor
    value = round(value, 1)

    if float(value).is_integer():
        return int(value)

    return value


def _parse_non_negative_decimal(
    raw_value,
    field_label,
):
    """
    Convierte un valor a Decimal y rechaza números negativos.
    """

    normalized_value = str(
        raw_value or "0"
    ).strip().replace(
        ",",
        ".",
    )

    try:
        value = Decimal(
            normalized_value
        )

    except (
        InvalidOperation,
        TypeError,
        ValueError,
    ):
        raise ValueError(
            f"{field_label} no es válido."
        )

    if value < 0:
        raise ValueError(
            f"{field_label} no puede ser negativo."
        )

    return value.quantize(
        Decimal("0.01")
    )


def _user_can_workpaper_action(
    user,
    action,
):
    """
    Determina si debe mostrarse una acción en la interfaz.
    El backend vuelve a validar cada operación.
    """

    return (
        user.is_superuser
        or user.is_staff
        or is_team_manager(user)
        or has_module_permission(
            user,
            "workpapers",
            action,
        )
    )


def _get_distribution_assignee(
    audit,
    assigned_auditor_id,
):
    """
    Valida que el responsable pertenezca al equipo
    de la auditoría seleccionada.
    """

    if not assigned_auditor_id:
        return None

    try:
        normalized_id = int(
            assigned_auditor_id
        )
    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "El responsable seleccionado no es válido."
        )

    allowed_ids = set(
        audit.assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    allowed_ids.add(
        audit.audit_manager_id
    )

    assigned_auditor = (
        User.objects
        .filter(
            id=normalized_id,
            id__in=allowed_ids,
            is_active=True,
            is_deleted=False,
        )
        .first()
    )

    if assigned_auditor is None:
        raise ValueError(
            "El responsable no pertenece al equipo de la auditoría."
        )

    return assigned_auditor


def _normalize_workpaper_datetime(
    value,
):
    """
    Normaliza date o datetime sin alterar la zona
    configurada por el proyecto.
    """

    if isinstance(
        value,
        datetime,
    ):
        return value

    if isinstance(
        value,
        date,
    ):
        return datetime.combine(
            value,
            time.min,
        )

    return timezone.now()


def _get_workpaper_status_options():
    """
    Garantiza los cinco estados definidos por la guía.
    """

    status_options = []

    for status_name, status_label in (
        WORKPAPER_STATUS_DEFINITIONS
    ):
        status, _created = (
            CurrentStatus.objects
            .get_or_create(
                name=status_name,
                defaults={
                    "verbose_name": (
                        status_label
                    ),
                },
            )
        )

        status_options.append(
            status
        )

    return status_options


def _ensure_default_workpapers(
    audit,
    pending_status,
):
    """
    Genera los 110 papeles cuando la auditoría todavía
    no tiene registros en este submódulo.

    Después de la generación inicial no repone
    automáticamente registros eliminados.
    """

    existing = (
        WorkingPapersStatus.objects
        .filter(
            audit=audit,
        )
        .exists()
    )

    if existing:
        return 0

    start_date = (
        _normalize_workpaper_datetime(
            audit.fechaInit
        )
    )

    end_date = (
        _normalize_workpaper_datetime(
            audit.fechaEnd
        )
    )

    if end_date <= start_date:
        end_date = (
            start_date
            + timedelta(
                days=1
            )
        )

    now = timezone.now()

    records = [
        WorkingPapersStatus(
            auditor=audit.audit_manager,
            audit=audit,
            reference=paper[
                "reference"
            ],
            working_papers=paper[
                "working_papers"
            ],
            start_date=start_date,
            end_date=end_date,
            current_status=(
                pending_status
            ),
            observations=None,
            created_at=now,
            updated_at=now,
        )
        for paper in WORKPAPER_CATALOG
    ]

    with transaction.atomic():
        WorkingPapersStatus.objects.bulk_create(
            records
        )

    return len(
        records
    )


def _get_workpaper_assignee(
    audit,
    user_id,
):
    """
    Valida que el responsable pertenezca al equipo
    de la auditoría.
    """

    try:
        normalized_id = int(
            user_id
        )

    except (
        TypeError,
        ValueError,
    ):
        raise ValueError(
            "El responsable seleccionado no es válido."
        )

    valid_ids = set(
        audit.assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    valid_ids.add(
        audit.audit_manager_id
    )

    assignee = (
        User.objects
        .filter(
            id=normalized_id,
            id__in=valid_ids,
            is_active=True,
            is_deleted=False,
        )
        .first()
    )

    if assignee is None:
        raise ValueError(
            "El responsable no pertenece al equipo."
        )

    return assignee


from django.contrib import messages
from django.template.loader import get_template
from audits.types import Audit as AuditType
from audits.decorators import audit_manager_required, selected_audit_required
from audits.utils import get_assigned_audits, get_selected_audit
from tools.constants import AUDIT_TIME_SUMMARY_TOOLS, REPORT_ERROR_INSTANCES
from tools.utils import get_table, get_table_to_pdf
from users.decorators import superuser_required
from users.permissions import (
    has_module_permission,
    is_team_manager,
    module_permission_required,
)

# Import WeasyPrint only when needed to avoid startup errors if dependencies are missing
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    WEASYPRINT_AVAILABLE = False
    HTML = None
from .tables import (
    ActivitiesTable,
    AuditTimeSummaryTable,
    BaseActivitiesTable,
    BaseAuditTimeSummaryTable,
    BaseCurrencyTypesTable,
    BaseSummaryHoursWorkedTable,
    CurrencyTypesTable,
    SummaryHoursWorkedTable,
    WorkingPapersStatusesTable,
    BaseWorkingPapersStatusesTable,
)
from .models import (
    Activity,
    ActivityTotalDaysPerMonth,
    AuditTimeDistribution,
    AuditTimeSummary,
    Country,
    CurrencyType,
    Months,
    SummaryHoursWorked,
    WorkingPapersStatus,
    CurrentStatus,
)
from .services import (
    create_audit_time_summary as create_audit_time_summary_func,
    delete_audit_time_summary as delete_audit_time_summary_func,
    create_status_of_work_papers as create_status_of_work_papers_func,
    delete_status_of_work_papers as delete_status_of_work_papers_func,
    delete_summary_hours_worked as delete_summary_hours_worked_func,
    create_summary_hours_worked as create_summary_hours_worked_func,
    get_working_papers_time_line_dic,
    update_activity_total_worked_days,
    update_audit_time_summary as update_audit_time_summary_func,
    update_summary_hours_worked as update_summary_hours_worked_func,
    update_status_of_work_papers as update_status_of_work_papers_func,
    update_currency_type as update_currency_type_func,
    delete_currency_type as delete_currency_type_func,
    create_currency_type as create_currency_type_func,
    create_activity as create_activity_func,
    update_activity as update_activity_func,
    delete_activity as delete_activity_func,
)


# Helper function to generate PDF with proper error handling
def generate_pdf_response(html_content: str, base_url: str, filename: str) -> HttpResponse:
    """
    Generate a PDF response from HTML content.
    If WeasyPrint is not available, returns an error response.
    """
    if not WEASYPRINT_AVAILABLE:
        return HttpResponse(
            "PDF generation is not available. WeasyPrint dependencies are missing. "
            "Please install GTK libraries for Windows or contact your administrator.",
            status=503,
            content_type="text/plain"
        )

    try:
        res = HttpResponse(content_type="application/pdf")
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=base_url)
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res
    except Exception as e:
        return HttpResponse(
            f"Error generating PDF: {str(e)}",
            status=500,
            content_type="text/plain"
        )


@login_required
@module_permission_required(
    "workpapers",
    "view",
)
def tools_page(req: HttpRequest):
    """
    Pantalla principal del módulo Herramientas.

    La guía vigente define únicamente tres submódulos:
    - Resumen de Tiempo.
    - Estado de Papeles de Trabajo.
    - Cronograma de Actividades.
    """

    functional_tools = [
        {
            "number": "01",
            "name": "Resumen de Tiempo",
            "description": (
                "Compara días y horas planificadas frente a las "
                "ejecutadas por auditor, encargo y etapa."
            ),
            "icon": "bi-clock-history",
            "tone": "blue",
            "url_name": "audit_time_summary_index",
            "file": "1  Resumen de Tiempo.xlsx",
            "standard": "NIA 220 / 230 / 300 / 320",
            "status": "Disponible",
        },
        {
            "number": "02",
            "name": "Estado de Papeles de Trabajo",
            "description": (
                "Controla la preparación, revisión, aprobación "
                "y observaciones de cada papel de trabajo."
            ),
            "icon": "bi-files",
            "tone": "teal",
            "url_name": "status_of_work_papers_table",
            "file": "2 Estado Papales de Trabajo.xlsx",
            "standard": "Seguimiento documental",
            "status": "Disponible",
        },
        {
            "number": "03",
            "name": "Cronograma de Actividades",
            "description": (
                "Organiza actividades, responsables, fechas, "
                "duración y estado del plan de auditoría."
            ),
            "icon": "bi-calendar-range",
            "tone": "purple",
            "url_name": "activities_page",
            "file": "3 Cronograma de Actividades.xlsx",
            "standard": "Plan de auditoría",
            "status": "Disponible",
        },
    ]

    context = {
        "functional_tools": functional_tools,
        "total_tools": len(functional_tools),
        "available_tools": len(functional_tools),
        "available_formats": 1,
    }

    return render(
        req,
        "tools/tools.html",
        context,
    )


@login_required
@module_permission_required(
    "workpapers",
    "view",
)
def descargar_herramienta(
    req: HttpRequest,
    nombre_archivo,
):
    """
    Descarga únicamente las tres plantillas vigentes del módulo.
    """

    allowed_files = {
        "1  Resumen de Tiempo.xlsx",
        "2 Estado Papales de Trabajo.xlsx",
        "3 Cronograma de Actividades.xlsx",
    }

    if nombre_archivo not in allowed_files:
        raise Http404(
            "La herramienta solicitada no está disponible."
        )

    ruta_archivo = os.path.join(
        settings.BASE_DIR,
        "static",
        "template-modulo-herramienta",
        "MODULO HERRAMIENTAS",
        nombre_archivo,
    )

    if not os.path.isfile(ruta_archivo):
        raise Http404(
            "El archivo solicitado no existe."
        )

    response = FileResponse(
        open(ruta_archivo, "rb"),
        as_attachment=True,
        filename=nombre_archivo,
    )

    return response


@login_required
@selected_audit_required(
    module="workpapers",
    action="view",
)
def audit_time_summary_index(
    req: HttpRequest,
):
    """
    Panel principal del Resumen de Tiempo.

    Incluye:
    - Personal y días por auditor.
    - Horas registradas por mes.
    - Distribución por etapa.
    - Distribución por componente.
    """

    selected_audit = (
        req.session.get(
            "selected_audit"
        )
        or {}
    )

    selected_audit_id = (
        selected_audit.get(
            "id"
        )
    )

    audit = req.selected_audit

    # La selección de auditoría no es una operación
    # de creación, actualización o eliminación.
    if (
        req.method == "POST"
        and req.POST.get("audit")
        and not req.POST.get("distribution_action")
    ):
        return redirect("audit_time_summary_index")

    if req.method == "POST":
        distribution_action = (
            req.POST.get(
                "distribution_action",
                "",
            )
            .strip()
            .lower()
        )

        try:
            if distribution_action == "create":
                audit = (
                    get_selected_audit_for_user_or_404(
                        req,
                        action="create",
                    )
                )

                distribution_type = (
                    req.POST.get(
                        "distribution_type",
                        "",
                    )
                    .strip()
                )

                valid_types = {
                    value
                    for value, _label
                    in AuditTimeDistribution.TYPE_CHOICES
                }

                if distribution_type not in valid_types:
                    raise ValueError(
                        "El tipo de distribución no es válido."
                    )

                name = (
                    req.POST.get(
                        "name",
                        "",
                    )
                    .strip()
                )

                if not name:
                    raise ValueError(
                        "Ingresa el nombre de la etapa o componente."
                    )

                planned_hours = (
                    _parse_non_negative_decimal(
                        req.POST.get(
                            "planned_hours"
                        ),
                        "Las horas planificadas",
                    )
                )

                actual_hours = (
                    _parse_non_negative_decimal(
                        req.POST.get(
                            "actual_hours"
                        ),
                        "Las horas reales",
                    )
                )

                materiality = (
                    req.POST.get(
                        "materiality",
                        "",
                    )
                    .strip()
                )

                risk_level = (
                    req.POST.get(
                        "risk_level",
                        "",
                    )
                    .strip()
                )

                status = (
                    req.POST.get(
                        "status",
                        "pending",
                    )
                    .strip()
                )

                valid_materialities = {
                    value
                    for value, _label
                    in AuditTimeDistribution.MATERIALITY_CHOICES
                }

                valid_risks = {
                    value
                    for value, _label
                    in AuditTimeDistribution.RISK_CHOICES
                }

                valid_statuses = {
                    value
                    for value, _label
                    in AuditTimeDistribution.STATUS_CHOICES
                }

                if materiality not in valid_materialities:
                    raise ValueError(
                        "La materialidad seleccionada no es válida."
                    )

                if risk_level not in valid_risks:
                    raise ValueError(
                        "El riesgo seleccionado no es válido."
                    )

                if status not in valid_statuses:
                    raise ValueError(
                        "El estado seleccionado no es válido."
                    )

                assigned_auditor = (
                    _get_distribution_assignee(
                        audit,
                        req.POST.get(
                            "assigned_auditor"
                        ),
                    )
                )

                AuditTimeDistribution.objects.create(
                    audit=audit,
                    created_by=req.user,
                    assigned_auditor=(
                        assigned_auditor
                    ),
                    distribution_type=(
                        distribution_type
                    ),
                    name=name,
                    planned_hours=(
                        planned_hours
                    ),
                    actual_hours=actual_hours,
                    materiality=materiality,
                    risk_level=risk_level,
                    status=status,
                    observations=(
                        req.POST.get(
                            "observations",
                            "",
                        )
                        .strip()
                    ),
                )

                messages.success(
                    req,
                    (
                        "La distribución de tiempo "
                        "fue creada correctamente."
                    ),
                )

            elif distribution_action == "update":
                record = (
                    get_tool_record_for_user_or_404(
                        request=req,
                        model=AuditTimeDistribution,
                        record_id=(
                            req.POST.get(
                                "record_id"
                            )
                        ),
                        action="edit",
                        queryset=(
                            AuditTimeDistribution.objects
                            .select_related(
                                "audit",
                                "assigned_auditor",
                            )
                        ),
                    )
                )

                name = (
                    req.POST.get(
                        "name",
                        "",
                    )
                    .strip()
                )

                if not name:
                    raise ValueError(
                        "Ingresa el nombre de la etapa o componente."
                    )

                materiality = (
                    req.POST.get(
                        "materiality",
                        "",
                    )
                    .strip()
                )

                risk_level = (
                    req.POST.get(
                        "risk_level",
                        "",
                    )
                    .strip()
                )

                status = (
                    req.POST.get(
                        "status",
                        "pending",
                    )
                    .strip()
                )

                valid_materialities = {
                    value
                    for value, _label
                    in AuditTimeDistribution.MATERIALITY_CHOICES
                }

                valid_risks = {
                    value
                    for value, _label
                    in AuditTimeDistribution.RISK_CHOICES
                }

                valid_statuses = {
                    value
                    for value, _label
                    in AuditTimeDistribution.STATUS_CHOICES
                }

                if materiality not in valid_materialities:
                    raise ValueError(
                        "La materialidad seleccionada no es válida."
                    )

                if risk_level not in valid_risks:
                    raise ValueError(
                        "El riesgo seleccionado no es válido."
                    )

                if status not in valid_statuses:
                    raise ValueError(
                        "El estado seleccionado no es válido."
                    )

                record.name = name
                record.planned_hours = (
                    _parse_non_negative_decimal(
                        req.POST.get(
                            "planned_hours"
                        ),
                        "Las horas planificadas",
                    )
                )
                record.actual_hours = (
                    _parse_non_negative_decimal(
                        req.POST.get(
                            "actual_hours"
                        ),
                        "Las horas reales",
                    )
                )
                record.assigned_auditor = (
                    _get_distribution_assignee(
                        record.audit,
                        req.POST.get(
                            "assigned_auditor"
                        ),
                    )
                )
                record.materiality = materiality
                record.risk_level = risk_level
                record.status = status
                record.observations = (
                    req.POST.get(
                        "observations",
                        "",
                    )
                    .strip()
                )

                record.save()

                messages.success(
                    req,
                    (
                        "La distribución de tiempo "
                        "fue actualizada correctamente."
                    ),
                )

            elif distribution_action == "delete":
                record = (
                    get_tool_record_for_user_or_404(
                        request=req,
                        model=AuditTimeDistribution,
                        record_id=(
                            req.POST.get(
                                "record_id"
                            )
                        ),
                        action="delete",
                    )
                )

                record.delete()

                messages.success(
                    req,
                    (
                        "La distribución de tiempo "
                        "fue eliminada correctamente."
                    ),
                )

            else:
                messages.error(
                    req,
                    "La operación solicitada no es válida.",
                )

        except IntegrityError:
            messages.error(
                req,
                (
                    "Ya existe una etapa o componente "
                    "con ese nombre en la auditoría."
                ),
            )

        except ValueError as error:
            messages.error(
                req,
                str(error),
            )

        except Http404:
            raise

        except Exception:
            messages.error(
                req,
                (
                    "No fue posible guardar la "
                    "distribución de tiempo."
                ),
            )

        return redirect(
            "audit_time_summary_index"
        )

    time_records = (
        AuditTimeSummary.objects
        .filter(
            audit_id=selected_audit_id,
        )
        .select_related(
            "assigned_auditor",
            "assigned_auditor__role",
        )
        .order_by(
            "appointment_number",
            "id",
        )
    )

    hours_records = (
        SummaryHoursWorked.objects
        .filter(
            audit_id=selected_audit_id,
        )
        .select_related(
            "month",
        )
        .order_by(
            "month_id",
            "id",
        )
    )

    distribution_records = (
        AuditTimeDistribution.objects
        .filter(
            audit_id=selected_audit_id,
        )
        .select_related(
            "assigned_auditor",
            "assigned_auditor__role",
        )
        .order_by(
            "distribution_type",
            "name",
            "id",
        )
    )

    stage_rows = [
        record
        for record in distribution_records
        if record.distribution_type
        == "stage"
    ]

    component_rows = [
        record
        for record in distribution_records
        if record.distribution_type
        == "component"
    ]

    time_totals = time_records.aggregate(
        planned=Sum(
            "scheduled_days"
        ),
        worked=Sum(
            "worked_days"
        ),
    )

    hours_totals = hours_records.aggregate(
        planned=Sum(
            "total_scheduled_hours"
        ),
        worked=Sum(
            "total_hours_worked"
        ),
    )

    planned_days = _duration_to_unit(
        time_totals["planned"],
        unit="days",
    )

    worked_days = _duration_to_unit(
        time_totals["worked"],
        unit="days",
    )

    planned_hours = _duration_to_unit(
        hours_totals["planned"],
        unit="hours",
    )

    worked_hours = _duration_to_unit(
        hours_totals["worked"],
        unit="hours",
    )

    difference_days = round(
        worked_days - planned_days,
        1,
    )

    difference_hours = round(
        worked_hours - planned_hours,
        1,
    )

    if float(difference_days).is_integer():
        difference_days = int(
            difference_days
        )

    if float(difference_hours).is_integer():
        difference_hours = int(
            difference_hours
        )

    if planned_days and worked_days:
        compliance = round(
            min(
                planned_days,
                worked_days,
            )
            / max(
                planned_days,
                worked_days,
            )
            * 100
        )
    elif planned_days:
        compliance = 0
    else:
        compliance = 0

    personnel_rows = []

    for record in time_records:
        row_planned_days = _duration_to_unit(
            record.scheduled_days,
            unit="days",
        )

        row_worked_days = _duration_to_unit(
            record.worked_days,
            unit="days",
        )

        row_difference = round(
            row_worked_days
            - row_planned_days,
            1,
        )

        if float(
            row_difference
        ).is_integer():
            row_difference = int(
                row_difference
            )

        if (
            row_planned_days
            and row_worked_days
        ):
            row_compliance = round(
                min(
                    row_planned_days,
                    row_worked_days,
                )
                / max(
                    row_planned_days,
                    row_worked_days,
                )
                * 100
            )
        elif row_planned_days:
            row_compliance = 0
        else:
            row_compliance = 0

        assigned_auditor = (
            record.assigned_auditor
        )

        auditor_name = (
            assigned_auditor.get_full_name()
            or assigned_auditor.username
        )

        role = getattr(
            assigned_auditor,
            "role",
            None,
        )

        role_label = (
            role.verbose_name
            if role
            else "Auditor"
        )

        personnel_rows.append({
            "record": record,
            "appointment_number": (
                record.appointment_number
            ),
            "auditor_name": auditor_name,
            "role_label": role_label,
            "planned_days": (
                row_planned_days
            ),
            "worked_days": (
                row_worked_days
            ),
            "difference": (
                row_difference
            ),
            "compliance": (
                row_compliance
            ),
            "observations": (
                record.observations
                or "Sin observaciones"
            ),
        })

    monthly_rows = []

    for record in hours_records:
        row_planned_hours = (
            _duration_to_unit(
                record.total_scheduled_hours,
                unit="hours",
            )
        )

        row_worked_hours = (
            _duration_to_unit(
                record.total_hours_worked,
                unit="hours",
            )
        )

        row_difference = round(
            row_worked_hours
            - row_planned_hours,
            1,
        )

        if float(
            row_difference
        ).is_integer():
            row_difference = int(
                row_difference
            )

        if (
            row_planned_hours
            and row_worked_hours
        ):
            row_compliance = round(
                min(
                    row_planned_hours,
                    row_worked_hours,
                )
                / max(
                    row_planned_hours,
                    row_worked_hours,
                )
                * 100
            )
        elif row_planned_hours:
            row_compliance = 0
        else:
            row_compliance = 0

        monthly_rows.append({
            "record": record,
            "month_name": (
                record.month.name.capitalize()
            ),
            "planned_hours": (
                row_planned_hours
            ),
            "worked_hours": (
                row_worked_hours
            ),
            "difference": (
                row_difference
            ),
            "compliance": (
                row_compliance
            ),
            "observations": (
                record.observations
                or "Sin observaciones"
            ),
        })

    assigned_ids = list(
        audit.assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    auditor_options = (
        User.objects
        .filter(
            Q(
                id__in=assigned_ids
            )
            | Q(
                id=audit.audit_manager_id
            ),
            is_active=True,
            is_deleted=False,
        )
        .select_related(
            "role",
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    context = {
        "selected_audit": selected_audit,

        "planned_days": planned_days,
        "worked_days": worked_days,
        "difference_days": (
            difference_days
        ),

        "planned_hours": planned_hours,
        "worked_hours": worked_hours,
        "difference_hours": (
            difference_hours
        ),

        "compliance": compliance,

        "personnel_rows": (
            personnel_rows
        ),
        "monthly_rows": monthly_rows,
        "stage_rows": stage_rows,
        "component_rows": (
            component_rows
        ),

        "auditor_options": (
            auditor_options
        ),
        "status_choices": (
            AuditTimeDistribution.STATUS_CHOICES
        ),
        "materiality_choices": (
            AuditTimeDistribution.MATERIALITY_CHOICES
        ),
        "risk_choices": (
            AuditTimeDistribution.RISK_CHOICES
        ),

        "can_create_distribution": (
            _user_can_workpaper_action(
                req.user,
                "create",
            )
        ),
        "can_edit_distribution": (
            _user_can_workpaper_action(
                req.user,
                "edit",
            )
        ),
        "can_delete_distribution": (
            _user_can_workpaper_action(
                req.user,
                "delete",
            )
        ),

        "total_time_records": (
            len(personnel_rows)
        ),
        "total_hour_records": (
            len(monthly_rows)
        ),
    }

    return render(
        req,
        (
            "tools/"
            "audit-time-summary-index-page.html"
        ),
        context,
    )

# Views de pagina propia una o actualizar
@login_required
def audit_time_summary(
    req: HttpRequest,
    id: int,
):
    """
    Abre o actualiza un registro de Resumen de Tiempo.

    La autorización específica se realiza en:
    - audit_time_summary_page para GET.
    - update_audit_time_summary para POST.
    """

    if req.method == "GET":
        return audit_time_summary_page(
            req,
            id,
        )

    if req.method == "POST":
        return update_audit_time_summary(
            req,
            id,
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )

@login_required
@superuser_required
# REMOVED: audit_mark() router function - tools.AuditMarks system deprecated

@login_required
@superuser_required
def currency_type(req: HttpRequest, id: int):
    if req.method == "GET":
        return currency_type_page(req, id)
    if req.method == "POST":
        return update_currency_type(req, id)


@login_required
def activity(
    req: HttpRequest,
    id: int,
):
    """
    Abre o actualiza una actividad del cronograma.

    La autorización específica se realiza en:
    - activity_page para GET.
    - update_activity para POST.
    """

    if req.method == "GET":
        return activity_page(
            req,
            id,
        )

    if req.method == "POST":
        return update_activity(
            req,
            id,
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


@login_required
def summary_hours_worked(
    req: HttpRequest,
    id: int,
):
    """
    Abre o actualiza un registro de horas mensuales.

    La autorización específica se realiza en:
    - summary_hours_worked_page para GET.
    - update_summary_hours_worked para POST.
    """

    if req.method == "GET":
        return summary_hours_worked_page(
            req,
            id,
        )

    if req.method == "POST":
        return update_summary_hours_worked(
            req,
            id,
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


@login_required
def status_of_work_papers(
    req: HttpRequest,
    id: int,
):
    """
    Abre o actualiza un Estado de Papeles de Trabajo.

    La autorización específica se realiza en:
    - status_of_work_papers_page para GET.
    - update_status_of_work_papers para POST.
    """

    if req.method == "GET":
        return status_of_work_papers_page(
            req,
            id,
        )

    if req.method == "POST":
        return update_status_of_work_papers(
            req,
            id,
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


# Views de creación pagina o back
@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
def audit_time_summary_create(
    req: HttpRequest,
):
    """
    Abre o procesa el formulario de creación.

    Exige Papeles de Trabajo → Crear sobre la
    auditoría seleccionada.
    """

    if req.method == "GET":
        return audit_time_summary_create_page(
            req
        )

    if req.method == "POST":
        return create_audit_time_summary(
            req
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )

@login_required
# @superuser_required
# REMOVED: audit_mark_create() router function - tools.AuditMarks system deprecated

@login_required
# @superuser_required
def currency_type_create(req: HttpRequest):
    if req.method == "GET":
        return create_currency_type_page(req)
    elif req.method == "POST":
        return create_currency_type(req)


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="create",
)
def activity_create(
    req: HttpRequest,
):
    """
    Abre o procesa el formulario de creación
    de actividades.

    Exige Papeles de Trabajo → Crear sobre la
    auditoría seleccionada.
    """

    if req.method == "GET":
        return activity_create_page(
            req
        )

    if req.method == "POST":
        return create_activity(
            req
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
def status_of_work_papers_create(
    req: HttpRequest,
):
    """
    Abre o procesa el formulario de creación.

    Exige Papeles de Trabajo → Crear sobre la
    auditoría seleccionada.
    """

    if req.method == "GET":
        return status_of_work_papers_create_page(
            req
        )

    if req.method == "POST":
        return create_status_of_work_papers(
            req
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
def summary_hours_worked_create(
    req: HttpRequest,
):
    """
    Abre o procesa el formulario de horas mensuales.

    Exige Papeles de Trabajo → Crear sobre la
    auditoría seleccionada.
    """

    if req.method == "GET":
        return summary_hours_worked_create_page(
            req
        )

    if req.method == "POST":
        return create_summary_hours_worked(
            req
        )

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )


# Views backend de creacion
@login_required
def create_audit_time_summary(req):
    audit = req.session.get("selected_audit")
    appointment_number = req.POST.get("appointment-number")
    scheduled_days = req.POST.get("scheduled-days")
    worked_days = req.POST.get("worked-days")
    observations = req.POST.get("observations")
    assigned_auditor = req.POST.get("assigned_auditor")
    try:
        create_audit_time_summary_func(
            req=req,
            audit=audit,
            appointment_number=appointment_number,
            scheduled_days=scheduled_days,
            worked_days=worked_days,
            observations=observations,
            assigned_auditor=assigned_auditor,
        )
        messages.success(req, "Resumen de tiempo de Auditoría creado exitosamente.")
        return redirect("audit_time_summary_table")

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados es inválido. "
                "Revisa la información e inténtalo nuevamente."
            ),
        )
        return redirect("create_audit_time_summary")

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(req, error_message)
            return redirect("create_audit_time_summary")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_audit_time_summary")


@login_required
# @superuser_required
# REMOVED: create_audit_mark() function (28 lines) - tools.AuditMarks system deprecated

@login_required
# @superuser_required
def create_currency_type(req: HttpRequest):
    name = req.POST.get("name")
    currency = req.POST.get("currency")
    country_id = req.POST.get("country")
    code = req.POST.get("code")
    try:
        create_currency_type_func(
            name=name, currency=currency, country_id=country_id, code=code
        )
        messages.success(req, "Tipo de moneda creado exitosamente.")

        return redirect("currency_types")

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados es inválido. "
                "Revisa la información e inténtalo nuevamente."
            ),
        )
        return redirect("create_currency_type")

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(req, error_message)
            return redirect("create_currency_type")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_currency_type")


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="create",
)
@require_POST
def create_activity(
    req: HttpRequest,
):
    """
    Crea una actividad dentro de la auditoría
    seleccionada.

    Exige Papeles de Trabajo → Crear.
    """

    audit: AuditType = req.session.get(
        "selected_audit"
    )

    observations = req.POST.get(
        "observations"
    )
    end_date = req.POST.get(
        "end-date"
    )
    start_date = req.POST.get(
        "start-date"
    )
    activity_name = req.POST.get(
        "activity"
    )
    current_status_id = req.POST.get(
        "current-status"
    )
    appointment_number = req.POST.get(
        "appointment-number"
    )

    try:
        create_activity_func(
            req=req,
            audit=audit,
            end_date=end_date,
            start_date=start_date,
            activity=activity_name,
            appointment_number=(
                appointment_number
            ),
            current_status_id=(
                current_status_id
            ),
            observations=observations,
        )

        messages.success(
            req,
            "Actividad creada exitosamente.",
        )

        return redirect(
            "activities_page"
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

        return redirect(
            "create_activity"
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

        return redirect(
            "create_activity"
        )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
@require_POST
def create_status_of_work_papers(
    req: HttpRequest,
):
    """
    Crea un Estado de Papeles de Trabajo dentro de
    la auditoría seleccionada.

    Exige Papeles de Trabajo → Crear.
    """

    audit: AuditType = req.session.get(
        "selected_audit"
    )

    working_papers = req.POST.get(
        "working-papers"
    )
    current_status = req.POST.get(
        "current-status"
    )
    observations = req.POST.get(
        "observations"
    )
    start_date_str = req.POST.get(
        "start-date"
    )
    end_date_str = req.POST.get(
        "end-date"
    )

    try:
        create_status_of_work_papers_func(
            req=req,
            audit=audit,
            working_papers=working_papers,
            current_status=current_status,
            start_date=start_date_str,
            end_date=end_date_str,
            observations=observations,
        )

        messages.success(
            req,
            (
                "Estado de Papeles de Trabajo "
                "creado exitosamente."
            ),
        )

        return redirect(
            "status_of_work_papers_table"
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

        return redirect(
            "create_status_of_work_papers"
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

        return redirect(
            "create_status_of_work_papers"
        )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
@require_POST
def create_summary_hours_worked(
    req: HttpRequest,
):
    """
    Crea un resumen mensual de horas para la
    auditoría seleccionada.

    Exige Papeles de Trabajo → Crear.
    """

    audit: AuditType = req.session.get(
        "selected_audit"
    )

    month = req.POST.get(
        "month"
    )
    total_scheduled_hours = req.POST.get(
        "scheduled-hours"
    )
    total_worked_hours = req.POST.get(
        "worked-hours"
    )
    observations = req.POST.get(
        "observations"
    )

    try:
        create_summary_hours_worked_func(
            req=req,
            audit=audit,
            month=month,
            total_scheduled_hours=(
                total_scheduled_hours
            ),
            total_worked_hours=(
                total_worked_hours
            ),
            observations=observations,
        )

        messages.success(
            req,
            (
                "Resumen de Horas Trabajadas "
                "creado exitosamente."
            ),
        )

        return redirect(
            "summary_worked_hours_table"
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

        return redirect(
            "create_summary_hours_worked"
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

        return redirect(
            "create_summary_hours_worked"
        )

# View backend de actualizar
@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="edit",
)
@require_POST
def update_audit_time_summary(
    req: HttpRequest,
    id: int,
):
    """
    Actualiza un registro de Resumen de Tiempo.

    Exige:
    - Papeles de Trabajo → Editar.
    - Auditoría seleccionada válida.
    - Registro perteneciente exactamente a esa auditoría.
    """

    audit_time_summary_to_update = (
        get_tool_record_for_user_or_404(
            request=req,
            model=AuditTimeSummary,
            record_id=id,
            action="edit",
            queryset=(
                AuditTimeSummary.objects
                .select_related(
                    "audit",
                    "auditor",
                    "assigned_auditor",
                    "assigned_auditor__role",
                )
            ),
        )
    )

    appointment_number = req.POST.get(
        "appointment-number"
    )
    scheduled_days = req.POST.get(
        "scheduled-days"
    )
    worked_days = req.POST.get(
        "worked-days"
    )
    observations = req.POST.get(
        "observations"
    )

    try:
        update_audit_time_summary_func(
            audit_time_summary_to_update=(
                audit_time_summary_to_update
            ),
            appointment_number=(
                appointment_number
            ),
            scheduled_days=(
                scheduled_days
            ),
            worked_days=worked_days,
            observations=observations,
        )

        messages.success(
            req,
            (
                "Resumen de tiempo de Auditoría "
                "actualizado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "audit_time_summary",
        id=id,
    )

# REMOVED: update_audit_mark() function (28 lines) - tools.AuditMarks system deprecated

@login_required
# @superuser_required
def update_currency_type(req: HttpRequest, id: int):
    currency_type = get_object_or_404(CurrencyType, pk=id)
    name = req.POST.get("name")
    currency = req.POST.get("currency")
    country_id = req.POST.get("country")
    code = req.POST.get("code")
    try:
        update_currency_type_func(
            currency_type_to_update=currency_type,
            name=name,
            currency=currency,
            country_id=country_id,
            code=code,
        )

        messages.success(req, "Tipo de moneda actualizado exitosamente.")
        return currency_types_page(req)
    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados es inválido. "
                "Revisa la información e inténtalo nuevamente."
            ),
        )
        return currency_type_page(req, id)

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(req, error_message)
            return currency_type_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return currency_type_page(req, id)


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="edit",
)
@require_POST
def update_activity(
    req: HttpRequest,
    id: int,
):
    """
    Actualiza una actividad del cronograma.

    Exige:
    - Papeles de Trabajo → Editar.
    - Auditoría seleccionada válida.
    - Actividad perteneciente exactamente a esa auditoría.
    """

    activity_to_update = (
        get_tool_record_for_user_or_404(
            request=req,
            model=Activity,
            record_id=id,
            action="edit",
            queryset=(
                Activity.objects
                .select_related(
                    "audit",
                    "created_by",
                    "current_status",
                )
                .prefetch_related(
                    "activity_total_days_per_month_activity",
                )
            ),
        )
    )

    observations = req.POST.get(
        "observations"
    )
    end_date = req.POST.get(
        "end-date"
    )
    start_date = req.POST.get(
        "start-date"
    )
    activity_name = req.POST.get(
        "activity"
    )
    current_status_id = req.POST.get(
        "current-status"
    )
    appointment_number = req.POST.get(
        "appointment-number"
    )

    try:
        update_activity_func(
            activity_to_update=(
                activity_to_update
            ),
            end_date=end_date,
            start_date=start_date,
            activity=activity_name,
            appointment_number=(
                appointment_number
            ),
            current_status_id=(
                current_status_id
            ),
            observations=observations,
        )

        messages.success(
            req,
            "Actividad actualizada exitosamente.",
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "activity",
        id=id,
    )

@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="edit",
)
@require_POST
def activity_total_days_per_month(
    req: HttpRequest,
    id: int,
):
    """
    Actualiza la distribución mensual de una actividad.

    Exige Papeles de Trabajo → Editar y que la actividad
    pertenezca a la auditoría seleccionada.
    """

    activity_to_update = (
        get_tool_record_for_user_or_404(
            request=req,
            model=Activity,
            record_id=id,
            action="edit",
            queryset=(
                Activity.objects
                .select_related(
                    "audit",
                    "created_by",
                    "current_status",
                )
            ),
        )
    )

    try:
        for field_name in req.POST:
            if not field_name.startswith(
                "month-"
            ):
                continue

            if "&" not in field_name:
                continue

            month_part, year_part = (
                field_name.split(
                    "&",
                    1,
                )
            )

            if (
                "-" not in month_part
                or "-" not in year_part
            ):
                continue

            month_id = month_part.split(
                "-",
                1,
            )[1]

            year_id = year_part.split(
                "-",
                1,
            )[1]

            total_days = req.POST.get(
                field_name
            )

            update_activity_total_worked_days(
                activity_to_update=(
                    activity_to_update
                ),
                month_id=month_id,
                total_days=total_days,
                year_id=year_id,
            )

        messages.success(
            req,
            (
                "Días totales trabajados "
                "actualizados exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "activity",
        id=activity_to_update.id,
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="edit",
)
@require_POST
def update_summary_hours_worked(
    req: HttpRequest,
    id: int,
):
    """
    Actualiza un resumen mensual de horas.

    Exige:
    - Papeles de Trabajo → Editar.
    - Auditoría seleccionada válida.
    - Registro perteneciente exactamente a esa auditoría.
    """

    summary_to_update = (
        get_tool_record_for_user_or_404(
            request=req,
            model=SummaryHoursWorked,
            record_id=id,
            action="edit",
            queryset=(
                SummaryHoursWorked.objects
                .select_related(
                    "audit",
                    "auditor",
                    "month",
                )
            ),
        )
    )

    month = req.POST.get(
        "month"
    )
    total_scheduled_hours = req.POST.get(
        "scheduled-hours"
    )
    total_hours_worked = req.POST.get(
        "worked-hours"
    )
    observations = req.POST.get(
        "observations"
    )

    try:
        update_summary_hours_worked_func(
            summary_hours_worked_to_update=(
                summary_to_update
            ),
            total_scheduled_hours=(
                total_scheduled_hours
            ),
            total_hours_worked=(
                total_hours_worked
            ),
            observations=observations,
            month=month,
        )

        messages.success(
            req,
            (
                "Resumen de horas trabajadas "
                "actualizado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "summary_hours_worked",
        id=id,
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="edit",
)
@require_POST
def update_status_of_work_papers(
    req: HttpRequest,
    id: int,
):
    """
    Actualiza un Estado de Papeles de Trabajo.

    Exige:
    - Papeles de Trabajo → Editar.
    - Auditoría seleccionada válida.
    - Registro perteneciente exactamente a esa auditoría.
    """

    status_to_update = (
        get_tool_record_for_user_or_404(
            request=req,
            model=WorkingPapersStatus,
            record_id=id,
            action="edit",
            queryset=(
                WorkingPapersStatus.objects
                .select_related(
                    "audit",
                    "auditor",
                    "current_status",
                )
            ),
        )
    )

    current_status = req.POST.get(
        "current-status"
    )
    end_date = req.POST.get(
        "end-date"
    )
    start_date = req.POST.get(
        "start-date"
    )
    working_papers = req.POST.get(
        "working-papers"
    )
    reference = req.POST.get(
        "reference"
    )
    observations = req.POST.get(
        "observations"
    )

    try:
        update_status_of_work_papers_func(
            status_of_work_papers_to_update=(
                status_to_update
            ),
            current_status=current_status,
            end_date=end_date,
            start_date=start_date,
            working_papers=working_papers,
            reference=reference,
            observations=observations,
        )

        messages.success(
            req,
            (
                "Estado de Papeles de Trabajo "
                "actualizado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados "
                "es inválido. Revisa la información "
                "e inténtalo nuevamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "status_of_work_papers",
        id=id,
    )

# Views backend de borrar
@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="delete",
)
@require_POST
def delete_audit_time_summary(
    req: HttpRequest,
    id: int,
):
    """
    Elimina un registro de Resumen de Tiempo.

    Exige:
    - Solicitud POST.
    - Papeles de Trabajo → Eliminar.
    - Registro perteneciente a la auditoría seleccionada.
    """

    audit_time_summary_to_delete = (
        get_tool_record_for_user_or_404(
            request=req,
            model=AuditTimeSummary,
            record_id=id,
            action="delete",
            queryset=(
                AuditTimeSummary.objects
                .select_related(
                    "audit",
                    "auditor",
                    "assigned_auditor",
                )
            ),
        )
    )

    try:
        delete_audit_time_summary_func(
            audit_time_summary_to_delete
        )

        messages.success(
            req,
            (
                "Resumen de tiempo de Auditoría "
                "eliminado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "No fue posible eliminar "
                "el registro solicitado."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "audit_time_summary_table"
    )


@login_required
# @superuser_required
# REMOVED: delete_audit_mark() function (25 lines) - tools.AuditMarks system deprecated

@login_required
# @superuser_required
def delete_currency_type(req: HttpRequest, id: int):
    currency_type_to_delete = get_object_or_404(CurrencyType, pk=id)
    try:
        delete_currency_type_func(currency_type_to_delete=currency_type_to_delete)
        messages.success(req, "Tipo de moneda eliminado exitosamente.")
        return redirect("currency_types")

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "Alguno de los valores ingresados es inválido. "
                "Revisa la información e inténtalo nuevamente."
            ),
        )
        return redirect("currency_types")

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(req, error_message)
            return redirect("currency_types")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("currency_types")


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="delete",
)
@require_POST
def delete_activity(
    req: HttpRequest,
    id: int,
):
    """
    Elimina una actividad del cronograma.

    Exige:
    - Solicitud POST.
    - Papeles de Trabajo → Eliminar.
    - Actividad perteneciente a la auditoría seleccionada.
    """

    activity_to_delete = (
        get_tool_record_for_user_or_404(
            request=req,
            model=Activity,
            record_id=id,
            action="delete",
            queryset=(
                Activity.objects
                .select_related(
                    "audit",
                    "created_by",
                    "current_status",
                )
            ),
        )
    )

    try:
        delete_activity_func(
            activity_to_delete
        )

        messages.success(
            req,
            "Actividad eliminada exitosamente.",
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "No fue posible eliminar "
                "la actividad solicitada."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "activities_page"
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="delete",
)
@require_POST
def delete_status_of_work_papers(
    req: HttpRequest,
    id: int,
):
    """
    Elimina un Estado de Papeles de Trabajo.

    Exige:
    - Solicitud POST.
    - Papeles de Trabajo → Eliminar.
    - Registro perteneciente a la auditoría seleccionada.
    """

    status_to_delete = (
        get_tool_record_for_user_or_404(
            request=req,
            model=WorkingPapersStatus,
            record_id=id,
            action="delete",
            queryset=(
                WorkingPapersStatus.objects
                .select_related(
                    "audit",
                    "auditor",
                    "current_status",
                )
            ),
        )
    )

    try:
        delete_status_of_work_papers_func(
            status_to_delete
        )

        messages.success(
            req,
            (
                "Estado de Papeles de Trabajo "
                "eliminado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "No fue posible eliminar "
                "el registro solicitado."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "status_of_work_papers_table"
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="delete",
)
@require_POST
def delete_summary_hours_worked(
    req: HttpRequest,
    id: int,
):
    """
    Elimina un resumen mensual de horas.

    Exige:
    - Solicitud POST.
    - Papeles de Trabajo → Eliminar.
    - Registro perteneciente a la auditoría seleccionada.
    """

    summary_to_delete = (
        get_tool_record_for_user_or_404(
            request=req,
            model=SummaryHoursWorked,
            record_id=id,
            action="delete",
            queryset=(
                SummaryHoursWorked.objects
                .select_related(
                    "audit",
                    "auditor",
                    "month",
                )
            ),
        )
    )

    try:
        delete_summary_hours_worked_func(
            summary_to_delete
        )

        messages.success(
            req,
            (
                "Resumen de Horas Trabajadas "
                "eliminado exitosamente."
            ),
        )

    except ValueError as error:
        messages.error(
            req,
            str(error)
            or (
                "No fue posible eliminar "
                "el registro solicitado."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            REPORT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado. "
                    "Inténtalo nuevamente."
                ),
            )

    return redirect(
        "summary_worked_hours_table"
    )

# Tables Pages
@login_required
@selected_audit_required("audit_time_summary_index")
def audit_time_summary_table_page(req: HttpRequest):
    """
    Listado de resúmenes de tiempo por auditor.

    Mantiene:
    - Búsqueda.
    - Paginación.
    - Creación.
    - Edición.
    - Eliminación.
    - Exportación PDF.
    """
    selected_audit: AuditType = req.session.get(
        "selected_audit"
    )

    if not selected_audit:
        return redirect("audit_time_summary_index")

    # ==========================================================
    # EXPORTACIÓN PDF EXISTENTE
    # ==========================================================
    if req.GET.get("generate_pdf") == "true":
        table = get_table_to_pdf(
            req,
            AuditTimeSummary,
            BaseAuditTimeSummaryTable,
            selected_audit=selected_audit,
        )

        context = {
            "table": table,
            "selected_audit": selected_audit,
        }

        template = get_template(
            "tools/audit-time-summaries_pdf.html"
        )

        html_content = template.render(context)

        filename = "resumen_de_tiempo_de_auditorias.pdf"

        return generate_pdf_response(
            html_content,
            req.build_absolute_uri("/"),
            filename,
        )

    # ==========================================================
    # REGISTROS DE LA AUDITORÍA SELECCIONADA
    # ==========================================================
    base_queryset = (
        AuditTimeSummary.objects
        .filter(
            auditor=req.user,
            audit_id=selected_audit["id"],
        )
        .select_related(
            "assigned_auditor",
            "assigned_auditor__role",
            "audit",
        )
        .order_by(
            "-created_at",
            "-id",
        )
    )

    search_query = req.GET.get(
        "q",
        "",
    ).strip()

    filtered_queryset = base_queryset

    if search_query:
        filtered_queryset = filtered_queryset.filter(
            Q(
                appointment_number__icontains=search_query
            )
            | Q(
                assigned_auditor__first_name__icontains=search_query
            )
            | Q(
                assigned_auditor__last_name__icontains=search_query
            )
            | Q(
                assigned_auditor__username__icontains=search_query
            )
            | Q(
                assigned_auditor__email__icontains=search_query
            )
            | Q(
                assigned_auditor__role__verbose_name__icontains=search_query
            )
            | Q(
                observations__icontains=search_query
            )
        )

    # ==========================================================
    # INDICADORES GENERALES
    # ==========================================================
    totals = base_queryset.aggregate(
        planned=Sum("scheduled_days"),
        worked=Sum("worked_days"),
        difference=Sum("differences"),
    )

    planned_days = _duration_to_unit(
        totals["planned"],
        unit="days",
    )

    worked_days = _duration_to_unit(
        totals["worked"],
        unit="days",
    )

    difference_days = _duration_to_unit(
        totals["difference"],
        unit="days",
    )

    if planned_days:
        general_compliance = round(
            worked_days / planned_days * 100
        )
    else:
        general_compliance = 0

    general_compliance = max(
        0,
        min(general_compliance, 100),
    )

    # ==========================================================
    # PAGINACIÓN
    # ==========================================================
    paginator = Paginator(
        filtered_queryset,
        15,
    )

    page_obj = paginator.get_page(
        req.GET.get("page")
    )

    summary_rows = []

    for record in page_obj.object_list:
        record_planned_days = _duration_to_unit(
            record.scheduled_days,
            unit="days",
        )

        record_worked_days = _duration_to_unit(
            record.worked_days,
            unit="days",
        )

        record_difference_days = _duration_to_unit(
            record.differences,
            unit="days",
        )

        if record_planned_days:
            progress = round(
                record_worked_days
                / record_planned_days
                * 100
            )
        else:
            progress = 0

        progress = max(
            0,
            min(progress, 100),
        )

        auditor_name = (
            record.assigned_auditor.get_full_name()
            or record.assigned_auditor.username
        )

        initials = "".join(
            part[0].upper()
            for part in auditor_name.split()
            if part
        )[:2]

        role = getattr(
            record.assigned_auditor,
            "role",
            None,
        )

        role_label = (
            role.verbose_name
            if role
            else "Auditor"
        )

        summary_rows.append({
            "record": record,
            "auditor_name": auditor_name,
            "initials": initials or "AU",
            "role_label": role_label,

            "planned_days": record_planned_days,
            "worked_days": record_worked_days,
            "difference_days": record_difference_days,

            "progress": progress,

            "observations": (
                record.observations
                or "Sin observaciones"
            ),
        })

    # ==========================================================
    # DISPONIBILIDAD PARA AGREGAR REGISTROS
    # ==========================================================
    registered_auditor_ids = set(
        base_queryset.values_list(
            "assigned_auditor_id",
            flat=True,
        )
    )

    assigned_users = (
        selected_audit.get("assigned_users")
        or []
    )

    available_auditors = [
        auditor
        for auditor in assigned_users
        if auditor.get("id")
        not in registered_auditor_ids
    ]

    context = {
        "selected_audit": selected_audit,

        "summary_rows": summary_rows,
        "page_obj": page_obj,

        "search_query": search_query,
        "filtered_count": filtered_queryset.count(),

        "total_records": base_queryset.count(),
        "planned_days": planned_days,
        "worked_days": worked_days,
        "difference_days": difference_days,
        "general_compliance": general_compliance,

        "available_auditors": available_auditors,
        "can_create_record": bool(
            available_auditors
        ),
    }

    return render(
        req,
        "tools/audit-time-summary.html",
        context,
    )


# REMOVED: audit_marks_page() function (32 lines) - tools.AuditMarks system deprecated

@login_required
def currency_types_page(req: HttpRequest):
    search_query = req.GET.get("q", "")
    data = {"request": req}
    if req.GET.get("generate_pdf") == "true":
        table = get_table_to_pdf(
            req,
            CurrencyType,
            BaseCurrencyTypesTable,
        )

        data["table"] = table

        # Generamos el PDF
        template = get_template("tools/currency-types_pdf.html")
        html_content = template.render(data)

        filename = f"tipos-de-moneda.pdf"
        return generate_pdf_response(html_content, req.build_absolute_uri("/"), filename)

    table = get_table(
        req=req,
        search_query=search_query,
        Model=CurrencyType,
        TableClass=(
            CurrencyTypesTable if req.user.is_superuser else BaseCurrencyTypesTable
        ),
        filters=("symbol", "name", "country"),
        confirmation_field="name" if req.user.is_superuser else None,
        delete_url="delete_currency_type" if req.user.is_superuser else None,
        edit_url="currency_type" if req.user.is_superuser else None,
    )
    context = {"table": table}
    return render(req, "tools/currency-types-page.html", context)


CRONOGRAMA_BASE = [
    ("A", "Planificación"),
    ("B", "Evaluación de Control Interno"),
    ("C", "Efectivo y Equivalentes"),
    ("D", "Cuentas por Cobrar"),
    ("E", "Inventarios"),
    ("F", "Activos Fijos"),
    ("G", "Pasivos"),
    ("H", "Ingresos"),
    ("I", "Gastos"),
    ("J", "Informe Borrador"),
    ("K", "Informe Final"),
]

MESES_CORTOS = [
    "ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
    "JUL", "AGO", "SEP", "OCT", "NOV", "DIC",
]


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    raise ValueError("La auditoría no tiene fechas válidas.")


def _ensure_cronograma_base(audit, pending_status):
    if Activity.objects.filter(audit=audit).exists():
        return 0

    start = _as_datetime(audit.fechaInit)
    end = _as_datetime(audit.fechaEnd)

    if end <= start:
        end = start + timedelta(days=1)

    members = list(
        User.objects.filter(
            Q(id__in=audit.assigned_users.values_list("id", flat=True))
            | Q(id=audit.audit_manager_id),
            is_active=True,
            is_deleted=False,
        )
        .distinct()
        .order_by("first_name", "last_name", "username")
    ) or [audit.audit_manager]

    duration = end - start
    split_dates = duration.days >= len(CRONOGRAMA_BASE)

    with transaction.atomic():
        for index, (reference, name) in enumerate(CRONOGRAMA_BASE, start=1):
            if split_dates:
                activity_start = start + duration * ((index - 1) / len(CRONOGRAMA_BASE))
                activity_end = start + duration * (index / len(CRONOGRAMA_BASE))
            else:
                activity_start = start
                activity_end = end

            Activity.objects.create(
                created_by=members[(index - 1) % len(members)],
                audit=audit,
                activity=name,
                reference=reference,
                appointment_number=f"ACT-{index:02d}",
                start_date=activity_start,
                end_date=activity_end,
                current_status=pending_status,
            )

    return len(CRONOGRAMA_BASE)


def _cronograma_status(record):
    name = str(record.current_status.name or "").lower()
    label = str(record.current_status.verbose_name or "").lower()

    if name == "approved" or "aprob" in label:
        return "approved", "Aprobado"

    if name in {"prepared", "in_progress", "in_review"} or "revisi" in label:
        return "review", "Revisión"

    return "pending", "Pendiente"


def _cronograma_months(start_value, end_value):
    start = _as_datetime(start_value).date()
    end = _as_datetime(end_value).date()
    current = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    months = []

    while current <= last:
        months.append({
            "year": current.year,
            "month": current.month,
            "label": MESES_CORTOS[current.month - 1],
        })
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )

    return months


def _days_in_month(activity, year, month):
    start = _as_datetime(activity.start_date).date()
    end = _as_datetime(activity.end_date).date()
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])
    overlap_start = max(start, month_start)
    overlap_end = min(end, month_end)

    if overlap_end < overlap_start:
        return 0

    return max((overlap_end - overlap_start).days, 1)


@login_required
@selected_audit_required(
    module="workpapers",
    action="view",
)
def activities_page(req: HttpRequest):
    """Cronograma de 11 actividades y vista mensual tipo Gantt."""

    audit = req.selected_audit
    selected_audit = req.session.get("selected_audit") or {}

    statuses = _get_workpaper_status_options()
    pending_status = next(status for status in statuses if status.name == "pending")

    created = _ensure_cronograma_base(audit, pending_status)
    if created:
        messages.success(req, f"Se generaron {created} actividades del cronograma.")

    if req.GET.get("generate_pdf") == "true":
        table = get_table_to_pdf(
            req,
            Activity,
            BaseActivitiesTable,
            selected_audit=selected_audit,
        )
        template = get_template("tools/activities_pdf.html")
        html_content = template.render({
            "table": table,
            "selected_audit": selected_audit,
        })
        return generate_pdf_response(
            html_content,
            req.build_absolute_uri("/"),
            "cronograma-de-actividades.pdf",
        )

    queryset = list(
        Activity.objects.filter(audit=audit)
        .select_related("created_by", "created_by__role", "current_status")
        .order_by("start_date", "id")
    )

    search_query = req.GET.get("q", "").strip().lower()
    rows = []

    for number, record in enumerate(queryset, start=1):
        responsible = record.created_by.get_full_name() or record.created_by.username
        status_key, status_label = _cronograma_status(record)

        row = {
            "number": number,
            "record": record,
            "responsible": responsible,
            "status_key": status_key,
            "status_label": status_label,
            "days": max((record.end_date - record.start_date).days, 1),
        }

        haystack = " ".join([
            record.activity or "",
            record.reference or "",
            record.appointment_number or "",
            responsible,
            record.observations or "",
        ]).lower()

        if not search_query or search_query in haystack:
            rows.append(row)

    approved = sum(1 for row in rows if row["status_key"] == "approved")
    review = sum(1 for row in rows if row["status_key"] == "review")
    pending = sum(1 for row in rows if row["status_key"] == "pending")
    total = len(rows)
    progress = round((approved + review) / total * 100) if total else 0
    total_days = sum(row["days"] for row in rows)

    months = _cronograma_months(audit.fechaInit, audit.fechaEnd)
    gantt_rows = []

    for row in rows:
        gantt_rows.append({
            "record": row["record"],
            "status_key": row["status_key"],
            "cells": [
                _days_in_month(row["record"], month["year"], month["month"])
                for month in months
            ],
        })

    month_totals = [
        sum(gantt_row["cells"][index] for gantt_row in gantt_rows)
        for index, _month in enumerate(months)
    ]

    return render(
        req,
        "tools/activities-page.html",
        {
            "selected_audit": selected_audit,
            "activity_rows": rows,
            "gantt_rows": gantt_rows,
            "months": months,
            "month_totals": month_totals,
            "search_query": search_query,
            "total_activities": total,
            "total_days": total_days,
            "approved_count": approved,
            "review_count": review,
            "pending_count": pending,
            "progress": progress,
            "can_create_activities": _user_can_workpaper_action(req.user, "create"),
            "can_edit_activities": _user_can_workpaper_action(req.user, "edit"),
            "can_delete_activities": _user_can_workpaper_action(req.user, "delete"),
        },
    )


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="view",
)
def summary_hours_worked_table_page(
    req: HttpRequest,
):
    search_query = req.GET.get("q", "")
    data = {}
    selected_audit: AuditType = req.session.get("selected_audit")

    if req.GET.get("generate_pdf") == "true":
        # Aquí obtenemos la tabla base, solo con los datos esenciales para la impresión
        table = get_table_to_pdf(
            req,
            SummaryHoursWorked,
            BaseSummaryHoursWorkedTable,
            selected_audit=selected_audit,
        )

        data["table"] = table

        # Generamos el PDF
        template = get_template("tools/summaries-hours-worked_pdf.html")
        html_content = template.render(data)

        filename = f"resumen_de_tiempo_de_auditorías.pdf"
        return generate_pdf_response(html_content, req.build_absolute_uri("/"), filename)
    else:
        table = get_table(
            req=req,
            search_query=search_query,
            Model=SummaryHoursWorked,
            TableClass=SummaryHoursWorkedTable,
            filters=("month__name",),
            delete_url="delete_summary_hours_worked",
            edit_url="summary_hours_worked",
            selected_audit=selected_audit,
            confirmation_field="total_scheduled_hours",
        )
        data["table"] = table

    return render(req, "tools/summary-hours-worked.html", data)


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="view",
)
def status_of_work_papers_table_page(
    req: HttpRequest,
):
    """
    Vista de los papeles de trabajo del encargo.

    En una auditoría sin registros genera automáticamente
    los 110 papeles definidos por la guía.
    """

    audit = req.selected_audit

    status_options = (
        _get_workpaper_status_options()
    )

    status_by_id = {
        str(status.id): status
        for status in status_options
    }

    pending_status = next(
        status
        for status in status_options
        if status.name == "pending"
    )

    created_records = (
        _ensure_default_workpapers(
            audit,
            pending_status,
        )
    )

    if created_records:
        messages.success(
            req,
            (
                "Se generaron automáticamente "
                f"{created_records} papeles de trabajo."
            ),
        )

    if req.method == "POST":
        paper_action = (
            req.POST.get(
                "paper_action",
                "",
            )
            .strip()
            .lower()
        )

        record_id = req.POST.get(
            "record_id"
        )

        if paper_action == "update":
            record = (
                get_tool_record_for_user_or_404(
                    request=req,
                    model=WorkingPapersStatus,
                    record_id=record_id,
                    action="edit",
                    queryset=(
                        WorkingPapersStatus.objects
                        .select_related(
                            "audit",
                            "auditor",
                            "current_status",
                        )
                    ),
                )
            )

            try:
                selected_status = (
                    status_by_id.get(
                        str(
                            req.POST.get(
                                "current_status"
                            )
                        )
                    )
                )

                if selected_status is None:
                    raise ValueError(
                        "El estado seleccionado no es válido."
                    )

                assignee = (
                    _get_workpaper_assignee(
                        record.audit,
                        req.POST.get(
                            "auditor_id"
                        ),
                    )
                )

                observations = (
                    req.POST.get(
                        "observations",
                        "",
                    )
                    .strip()
                )

                WorkingPapersStatus.objects.filter(
                    pk=record.pk
                ).update(
                    auditor=assignee,
                    current_status=(
                        selected_status
                    ),
                    observations=(
                        observations
                        or None
                    ),
                    updated_at=timezone.now(),
                )

                messages.success(
                    req,
                    (
                        f"{record.reference} "
                        "actualizado correctamente."
                    ),
                )

            except ValueError as error:
                messages.error(
                    req,
                    str(error),
                )

        elif paper_action == "delete":
            record = (
                get_tool_record_for_user_or_404(
                    request=req,
                    model=WorkingPapersStatus,
                    record_id=record_id,
                    action="delete",
                )
            )

            reference = record.reference
            record.delete()

            messages.success(
                req,
                (
                    f"{reference} eliminado "
                    "correctamente."
                ),
            )

        else:
            messages.error(
                req,
                "La operación solicitada no es válida.",
            )

        return redirect(
            "status_of_work_papers_table"
        )

    selected_audit = (
        req.session.get(
            "selected_audit"
        )
        or {}
    )

    if (
        req.GET.get(
            "generate_pdf"
        )
        == "true"
    ):
        table = get_table_to_pdf(
            req,
            WorkingPapersStatus,
            BaseWorkingPapersStatusesTable,
            selected_audit=(
                selected_audit
            ),
        )

        template = get_template(
            (
                "tools/"
                "statuses-of-working-papers_pdf.html"
            )
        )

        html_content = template.render({
            "table": table,
            "selected_audit": (
                selected_audit
            ),
        })

        return generate_pdf_response(
            html_content,
            req.build_absolute_uri(
                "/"
            ),
            (
                "estado-de-papeles-"
                "de-trabajo.pdf"
            ),
        )

    base_queryset = (
        WorkingPapersStatus.objects
        .filter(
            audit=audit,
        )
        .select_related(
            "auditor",
            "auditor__role",
            "current_status",
        )
        .order_by(
            "reference",
            "id",
        )
    )

    total_records = (
        base_queryset.count()
    )

    status_counts = {
        status_name: (
            base_queryset.filter(
                current_status__name=(
                    status_name
                ),
            )
            .count()
        )
        for status_name, _label
        in WORKPAPER_STATUS_DEFINITIONS
    }

    approved_records = (
        status_counts.get(
            "approved",
            0,
        )
    )

    completion = (
        round(
            approved_records
            / total_records
            * 100
        )
        if total_records
        else 0
    )

    search_query = (
        req.GET.get(
            "q",
            "",
        )
        .strip()
    )

    status_filter = (
        req.GET.get(
            "status",
            "",
        )
        .strip()
    )

    filtered_queryset = (
        base_queryset
    )

    if search_query:
        filtered_queryset = (
            filtered_queryset
            .filter(
                Q(
                    reference__icontains=(
                        search_query
                    )
                )
                | Q(
                    working_papers__icontains=(
                        search_query
                    )
                )
                | Q(
                    auditor__first_name__icontains=(
                        search_query
                    )
                )
                | Q(
                    auditor__last_name__icontains=(
                        search_query
                    )
                )
                | Q(
                    auditor__username__icontains=(
                        search_query
                    )
                )
                | Q(
                    observations__icontains=(
                        search_query
                    )
                )
            )
        )

    valid_status_names = {
        status.name
        for status in status_options
    }

    if (
        status_filter
        in valid_status_names
    ):
        filtered_queryset = (
            filtered_queryset
            .filter(
                current_status__name=(
                    status_filter
                ),
            )
        )
    else:
        status_filter = ""

    paper_rows = [
        {
            "record": record,
            "phase": (
                get_workpaper_phase(
                    record.reference
                )
            ),
        }
        for record in filtered_queryset
    ]

    assigned_ids = list(
        audit.assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    auditor_options = (
        User.objects
        .filter(
            Q(
                id__in=assigned_ids
            )
            | Q(
                id=audit.audit_manager_id
            ),
            is_active=True,
            is_deleted=False,
        )
        .select_related(
            "role",
        )
        .distinct()
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    context = {
        "selected_audit": (
            selected_audit
        ),
        "paper_rows": paper_rows,
        "status_options": (
            status_options
        ),
        "auditor_options": (
            auditor_options
        ),

        "search_query": (
            search_query
        ),
        "status_filter": (
            status_filter
        ),
        "filtered_count": (
            len(paper_rows)
        ),

        "total_records": (
            total_records
        ),
        "pending_records": (
            status_counts.get(
                "pending",
                0,
            )
        ),
        "prepared_records": (
            status_counts.get(
                "prepared",
                0,
            )
        ),
        "in_progress_records": (
            status_counts.get(
                "in_progress",
                0,
            )
        ),
        "in_review_records": (
            status_counts.get(
                "in_review",
                0,
            )
        ),
        "approved_records": (
            approved_records
        ),
        "completion": completion,

        "can_edit_papers": (
            _user_can_workpaper_action(
                req.user,
                "edit",
            )
        ),
        "can_delete_papers": (
            _user_can_workpaper_action(
                req.user,
                "delete",
            )
        ),
    }

    return render(
        req,
        "tools/status-of-work-papers.html",
        context,
    )

# Vistas para crear
@login_required
# @superuser_required
# REMOVED: create_audit_mark_page() function (2 lines) - tools.AuditMarks system deprecated

@login_required
# @superuser_required
def create_currency_type_page(req: HttpRequest):
    countries = Country.objects.exclude(id__in=CurrencyType.objects.values("country"))
    context = {"countries": countries}
    return render(req, "tools/create-currency-type.html", context)


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="create",
)
def activity_create_page(
    req: HttpRequest,
):
    """
    Muestra el formulario para crear una actividad.
    """

    return render(
        req,
        "tools/create-activity-page.html",
    )


@login_required
def audit_time_summary_create_page(
    req: HttpRequest,
):
    """
    Prepara el formulario de creación de un resumen
    de tiempo para la auditoría seleccionada.
    """
    selected_audit: AuditType = req.session.get(
        "selected_audit"
    )

    if not selected_audit:
        return redirect("audit_time_summary_index")

    assigned_auditor_ids = set(
        AuditTimeSummary.objects.filter(
            audit_id=selected_audit["id"],
        ).values_list(
            "assigned_auditor_id",
            flat=True,
        )
    )

    auditors_to_select = [
        auditor
        for auditor in (
            selected_audit.get("assigned_users")
            or []
        )
        if auditor.get("id")
        not in assigned_auditor_ids
    ]

    auditors_to_select.sort(
        key=lambda auditor: (
            auditor.get("first_name", "").lower(),
            auditor.get("last_name", "").lower(),
            auditor.get("username", "").lower(),
        )
    )

    context = {
        "selected_audit": selected_audit,
        "auditors_to_select": auditors_to_select,
        "can_create_record": bool(
            auditors_to_select
        ),
    }

    return render(
        req,
        "tools/create-audit-time-summary.html",
        context,
    )


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
def status_of_work_papers_create_page(
    req: HttpRequest,
):
    """
    Muestra el formulario para crear un Estado
    de Papeles de Trabajo.
    """

    return render(
        req,
        "tools/create-status-of-work-papers.html",
    )


@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="create",
)
def summary_hours_worked_create_page(
    req: HttpRequest,
):
    audit: AuditType = req.session.get("selected_audit")

    related_months = [
        summary_hours_worked.month
        for summary_hours_worked in SummaryHoursWorked.objects.filter(
            audit__pk=int(audit["id"])
        )
    ]
    # Filtrar los meses que no están en related_months
    missing_months = [
        month for month in Months.objects.all() if month not in related_months
    ]
    data = {
        "months": missing_months,
        "audits": get_assigned_audits(user_role=req.user.role.name, req=req),
    }
    return render(req, "tools/create-summary-hours-worked.html", data)


# Vistas para un registro solo
@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="view",
)
def audit_time_summary_page(
    req: HttpRequest,
    id: int,
):
    """
    Muestra un registro individual de Resumen de Tiempo.

    El registro debe pertenecer exactamente a la
    auditoría seleccionada.
    """

    audit_time_summary = (
        get_tool_record_for_user_or_404(
            request=req,
            model=AuditTimeSummary,
            record_id=id,
            action="view",
            queryset=(
                AuditTimeSummary.objects
                .select_related(
                    "audit",
                    "auditor",
                    "assigned_auditor",
                    "assigned_auditor__role",
                )
            ),
        )
    )

    data = {
        "audit_time_summary": (
            audit_time_summary
        ),
    }

    if (
        req.GET.get(
            "generate_pdf"
        )
        == "true"
    ):
        template = get_template(
            "tools/audit-time-summary_pdf.html"
        )

        html_content = template.render(
            data
        )

        filename = (
            "reporte_de_resumen_de_tiempo_"
            "de_auditoría-nombramiento_no_"
            f"{audit_time_summary.appointment_number}"
            ".pdf"
        )

        return generate_pdf_response(
            html_content,
            req.build_absolute_uri(
                "/"
            ),
            filename,
        )

    scheduled_seconds = (
        audit_time_summary
        .scheduled_days
        .total_seconds()
    )

    worked_seconds = (
        audit_time_summary
        .worked_days
        .total_seconds()
    )

    if scheduled_seconds > 0:
        progress = round(
            worked_seconds
            / scheduled_seconds
            * 100
        )
    else:
        progress = 0

    data["progress"] = max(
        0,
        min(
            progress,
            100,
        ),
    )

    return render(
        req,
        "tools/audit-time-summary-page.html",
        data,
    )


# REMOVED: audit_mark_page() function (4 lines) - tools.AuditMarks system deprecated

@login_required
@superuser_required
def currency_type_page(req: HttpRequest, id: int):
    currency_type = get_object_or_404(CurrencyType, pk=id)
    # Excluir los países asignados en CurrencyType, excepto el país actual de currency_type
    countries = Country.objects.exclude(
        ~Q(id=currency_type.country_id)
        & Q(id__in=CurrencyType.objects.values("country"))
    )

    context = {"currency_type": currency_type, "countries": countries}
    return render(req, "tools/currency-type-page.html", context)


@login_required
@selected_audit_required(
    "activities_page",
    module="workpapers",
    action="view",
)
def activity_page(
    req: HttpRequest,
    id: int,
):
    """
    Muestra una actividad del cronograma.

    La actividad debe pertenecer exactamente a la
    auditoría seleccionada.
    """

    activity_record = (
        get_tool_record_for_user_or_404(
            request=req,
            model=Activity,
            record_id=id,
            action="view",
            queryset=(
                Activity.objects
                .select_related(
                    "audit",
                    "created_by",
                    "current_status",
                )
                .prefetch_related(
                    "activity_total_days_per_month_activity",
                )
            ),
        )
    )

    context = {
        "activity": activity_record,
        "total_days_per_month_list": (
            activity_record
            .get_activity_total_days_per_month_list_dict()
        ),
    }

    return render(
        req,
        "tools/activity-page.html",
        context,
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="view",
)
def status_of_work_papers_page(
    req: HttpRequest,
    id: int,
):
    """
    Muestra un Estado de Papeles de Trabajo.

    El registro debe pertenecer exactamente a la
    auditoría seleccionada.
    """

    status_of_work_papers = (
        get_tool_record_for_user_or_404(
            request=req,
            model=WorkingPapersStatus,
            record_id=id,
            action="view",
            queryset=(
                WorkingPapersStatus.objects
                .select_related(
                    "audit",
                    "auditor",
                    "current_status",
                )
            ),
        )
    )

    data = {
        "status_of_work_papers": (
            status_of_work_papers
        ),
    }

    if (
        req.GET.get(
            "generate_pdf"
        )
        == "true"
    ):
        template = get_template(
            "tools/status-of-work-papers_pdf.html"
        )

        html_content = template.render(
            data
        )

        filename = (
            "reporte_de_estado_de_papeles_"
            "de_trabajo-referencia_"
            f"{status_of_work_papers.reference}.pdf"
        )

        return generate_pdf_response(
            html_content,
            req.build_absolute_uri(
                "/"
            ),
            filename,
        )

    time_line = (
        get_working_papers_time_line_dic(
            status_of_work_papers
            .current_status
            .name
        )
    )

    data["time_line"] = time_line

    return render(
        req,
        "tools/status-of-work-papers-page.html",
        data,
    )

@login_required
@selected_audit_required(
    "audit_time_summary_index",
    module="workpapers",
    action="view",
)
def summary_hours_worked_page(
    req: HttpRequest,
    id: int,
):
    """
    Muestra un resumen mensual de horas.

    El registro debe pertenecer exactamente a la
    auditoría seleccionada.
    """

    summary_hours_worked = (
        get_tool_record_for_user_or_404(
            request=req,
            model=SummaryHoursWorked,
            record_id=id,
            action="view",
            queryset=(
                SummaryHoursWorked.objects
                .select_related(
                    "audit",
                    "auditor",
                    "month",
                )
            ),
        )
    )

    data = {
        "summary_hours_worked": (
            summary_hours_worked
        ),
    }

    if (
        req.GET.get(
            "generate_pdf"
        )
        == "true"
    ):
        template = get_template(
            "tools/summary-hours-worked_pdf.html"
        )

        html_content = template.render(
            data
        )

        filename = (
            "reporte_de_resumen_de_horas_"
            "trabajadas_del_mes-"
            f"{summary_hours_worked.month.name.lower()}"
            ".pdf"
        )

        return generate_pdf_response(
            html_content,
            req.build_absolute_uri(
                "/"
            ),
            filename,
        )

    scheduled_seconds = (
        summary_hours_worked
        .total_scheduled_hours
        .total_seconds()
    )

    worked_seconds = (
        summary_hours_worked
        .total_hours_worked
        .total_seconds()
    )

    if scheduled_seconds > 0:
        progress = int(
            worked_seconds
            / scheduled_seconds
            * 100
        )
    else:
        progress = 0

    data["progress"] = max(
        0,
        min(
            progress,
            100,
        ),
    )

    data["months"] = [
        {
            "id": month.pk,
            "name": month.name,
        }
        for month in Months.objects.all()
    ]

    return render(
        req,
        "tools/summary-hours-worked-page.html",
        data,
    )