from django.http import Http404, HttpRequest, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os

from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

from django.contrib import messages
from django.template.loader import get_template
from audits.types import Audit as AuditType
from audits.decorators import audit_manager_required, selected_audit_required
from audits.utils import get_assigned_audits, get_selected_audit
from tools.constants import AUDIT_TIME_SUMMARY_TOOLS, REPORT_ERROR_INSTANCES
from tools.utils import get_table, get_table_to_pdf
from users.decorators import superuser_required
from weasyprint import HTML
from .tables import (
    ActivitiesTable,
    AuditMarksTable,
    AuditTimeSummaryTable,
    BaseActivitiesTable,
    BaseAuditMarksTable,
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
    AuditMarks,
    AuditTimeSummary,
    Country,
    CurrencyType,
    Months,
    SummaryHoursWorked,
    WorkingPapersStatus,
    CurrentStatus,
    Months,
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
    create_audit_mark as create_audit_mark_func,
    update_audit_mark as update_audit_mark_func,
    delete_audit_mark as delete_audit_mark_func,
    update_currency_type as update_currency_type_func,
    delete_currency_type as delete_currency_type_func,
    create_currency_type as create_currency_type_func,
    create_activity as create_activity_func,
    update_activity as update_activity_func,
    delete_activity as delete_activity_func,
)


@login_required
def tools_page(req: HttpRequest):
    # Crear un diccionario con los nombres de los archivos para la plantilla
    context = {
        'documentos': [
            {'id': '1', 'nombre': '1 Resumen de Tiempo', 'archivo': '1  Resumen de Tiempo.xlsx'},
            {'id': '2', 'nombre': '2 Estado Papales de Trabajo', 'archivo': '2 Estado Papales de Trabajo.xlsx'},
            {'id': '3', 'nombre': '3 Cronograma de Actividades', 'archivo': '3 Cronograma de Actividades.xlsx'},
            {'id': '4', 'nombre': '4 Referencias Cruzadas Nías', 'archivo': '4 Referencias Cruzadas Nías.xlsx'},
            {'id': '5', 'nombre': '5 Matriz de Riesgos Vinculada', 'archivo': '5 Matriz de Riesgos Vinculada.xlsx'},
            {'id': '6', 'nombre': '6 Planificación', 'archivo': '6 Planificación.xlsx'},
            {'id': '7', 'nombre': '7 Evaluación de Procesos', 'archivo': '7 Evaluación de Procesos.xlsx'},
            {'id': '8', 'nombre': '8 Pruebas Sustantivas', 'archivo': '8 Pruebas Sustantivas.xlsx'},
            {'id': '9', 'nombre': '9 Finalización', 'archivo': '9  Finalización.xlsx'},
            {'id': '10', 'nombre': '10 Marcas de Auditoría', 'archivo': '10 Marcas_de_Auditoría.xlsx'},
        ]
    }
    return render(req, "tools/tools.html", context)


@login_required
def descargar_herramienta(req: HttpRequest, nombre_archivo):
    # Construir la ruta completa al archivo
    ruta_archivo = os.path.join(
        settings.BASE_DIR, 
        'static', 
        'template-modulo-herramienta',
        'MODULO HERRAMIENTAS',
        nombre_archivo
    )
    
    # Verificar si el archivo existe
    if os.path.exists(ruta_archivo):
        # Abrir el archivo en modo binario y devolverlo como respuesta
        archivo = open(ruta_archivo, 'rb')
        response = FileResponse(archivo)
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
        return response
    else:
        # Si el archivo no existe, devolver un error 404
        raise Http404("El archivo solicitado no existe.")


@login_required
@selected_audit_required
def audit_time_summary_index(req: HttpRequest):
    context = {
        "tools": AUDIT_TIME_SUMMARY_TOOLS,
        "audits": get_assigned_audits(user_role=req.user.role.name, req=req),
    }

    return render(req, "tools/audit-time-summary-index-page.html", context)


# Views de pagina propia una o actualizar
@login_required
def audit_time_summary(req: HttpRequest, id: int):
    if req.method == "GET":
        return audit_time_summary_page(req, id)
    elif req.method == "POST":
        return update_audit_time_summary(req, id)


@login_required
@superuser_required
def audit_mark(req: HttpRequest, id: int):
    if req.method == "GET":
        return audit_mark_page(req, id)
    if req.method == "POST":
        return update_audit_mark(req, id)


@login_required
@superuser_required
def currency_type(req: HttpRequest, id: int):
    if req.method == "GET":
        return currency_type_page(req, id)
    if req.method == "POST":
        return update_currency_type(req, id)


@login_required
def activity(req: HttpRequest, id: int):
    if req.method == "GET":
        return activity_page(req, id)
    if req.method == "POST":
        return update_activity(req, id)


@login_required
def summary_hours_worked(req: HttpRequest, id: int):
    if req.method == "GET":
        return summary_hours_worked_page(req, id)
    if req.method == "POST":
        return update_summary_hours_worked(req, id)


@login_required
def status_of_work_papers(req: HttpRequest, id: int):
    if req.method == "GET":
        return status_of_work_papers_page(req, id)
    if req.method == "POST":
        return update_status_of_work_papers(req, id)


# Views de creación pagina o back
@login_required
def audit_time_summary_create(req: HttpRequest):
    if req.method == "GET":
        return audit_time_summary_create_page(req)
    elif req.method == "POST":
        return create_audit_time_summary(req)


@login_required
# @superuser_required
def audit_mark_create(req: HttpRequest):
    if req.method == "GET":
        return create_audit_mark_page(req)
    elif req.method == "POST":
        return create_audit_mark(req)


@login_required
# @superuser_required
def currency_type_create(req: HttpRequest):
    if req.method == "GET":
        return create_currency_type_page(req)
    elif req.method == "POST":
        return create_currency_type(req)


@login_required
# @audit_manager_required
def activity_create(req: HttpRequest):
    if req.method == "GET":
        return activity_create_page(req)
    elif req.method == "POST":
        return create_activity(req)


@login_required
def status_of_work_papers_create(req: HttpRequest):
    if req.method == "GET":
        return status_of_work_papers_create_page(req)
    elif req.method == "POST":
        return create_status_of_work_papers(req)


@login_required
def summary_hours_worked_create(req: HttpRequest):
    if req.method == "GET":
        return summary_hours_worked_create_page(req)
    elif req.method == "POST":
        return create_summary_hours_worked(req)


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

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_audit_time_summary")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_audit_time_summary")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_audit_time_summary")


@login_required
# @superuser_required
def create_audit_mark(req: HttpRequest):
    name = req.POST.get("name")
    description = req.POST.get("description")
    image = req.POST.get("image")

    try:
        create_audit_mark_func(name=name, description=description, image=image)
        messages.success(req, "Marca de Auditoría creada exitosamente.")
        return redirect("audit_marks")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_audit_mark")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_audit_mark")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_audit_mark")


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

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_currency_type")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_currency_type")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_currency_type")


@login_required
@selected_audit_required("activities_page")
# @audit_manager_required
def create_activity(req: HttpRequest):
    audit: AuditType = req.session.get("selected_audit")
    observations = req.POST.get("observations")
    end_date = req.POST.get("end-date")
    start_date = req.POST.get("start-date")
    activity = req.POST.get("activity")
    current_status_id = req.POST.get("current-status")
    appointment_number = req.POST.get("appointment-number")
    try:
        create_activity_func(
            req=req,
            audit=audit,
            end_date=end_date,
            start_date=start_date,
            activity=activity,
            appointment_number=appointment_number,
            current_status_id=current_status_id,
            observations=observations,
        )
        messages.success(req, "Actividad creada exitosamente.")
        return redirect("activities_page")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_activity")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_activity")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_activity")


@login_required
@selected_audit_required("audit_time_summary_index")
def create_status_of_work_papers(req: HttpRequest):
    audit: AuditType = req.session.get("selected_audit")
    working_papers = req.POST.get("working-papers")
    current_status = req.POST.get("current-status")
    observations = req.POST.get("observations")
    start_date_str = req.POST.get("start-date")
    end_date_str = req.POST.get("end-date")
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
        messages.success(req, "Estado de Papeles de Trabajo creado exitosamente.")
        return redirect("status_of_work_papers_table")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_status_of_work_papers")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_status_of_work_papers")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_status_of_work_papers")


@login_required
@selected_audit_required("audit_time_summary_index")
def create_summary_hours_worked(req: HttpRequest):
    audit: AuditType = req.session.get("selected_audit")
    month = req.POST.get("month")
    total_scheduled_hours = req.POST.get("scheduled-hours")
    total_worked_hours = req.POST.get("worked-hours")
    observations = req.POST.get("observations")
    try:
        create_summary_hours_worked_func(
            req=req,
            audit=audit,
            month=month,
            total_scheduled_hours=total_scheduled_hours,
            total_worked_hours=total_worked_hours,
            observations=observations,
        )
        messages.success(req, "Resumen de Horas Trabajadas creado exitosamente.")
        return redirect("summary_worked_hours_table")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_summary_hours_worked")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_summary_hours_worked")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_summary_hours_worked")


# View backend de actualizar
@login_required
def update_audit_time_summary(req: HttpRequest, id: int):
    appointment_number = req.POST.get("appointment-number")
    scheduled_days = req.POST.get("scheduled-days")
    worked_days = req.POST.get("worked-days")
    observations = req.POST.get("observations")

    audit_time_summary_to_update = get_object_or_404(
        AuditTimeSummary, pk=id, auditor=req.user
    )
    try:
        update_audit_time_summary_func(
            audit_time_summary_to_update=audit_time_summary_to_update,
            appointment_number=appointment_number,
            scheduled_days=scheduled_days,
            worked_days=worked_days,
            observations=observations,
        )
        messages.success(
            req, "Resumen de tiempo de Auditoría actualizado exitosamente."
        )
        return audit_time_summary_page(req, id)

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return audit_time_summary_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return audit_time_summary_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return audit_time_summary_page(req, id)


@login_required
# @superuser_required
def update_audit_mark(req: HttpRequest, id: int):
    audit_mark_to_update = get_object_or_404(AuditMarks, pk=id)
    name = req.POST.get("name")
    description = req.POST.get("description")
    image = req.POST.get("image")

    try:
        update_audit_mark_func(audit_mark_to_update, name, description, image)
        messages.success(req, "Marca de Auditoría actualizada exitosamente.")
        return audit_marks_page(req)
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return audit_mark_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return audit_mark_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return audit_mark_page(req, id)


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
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return currency_type_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return currency_type_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return currency_type_page(req, id)


@login_required
# @audit_manager_required
def update_activity(req: HttpRequest, id: int):
    activity_to_update = get_object_or_404(
        Activity, pk=id, created_by=req.user, audit__audit_manager=req.user
    )
    observations = req.POST.get("observations")
    end_date = req.POST.get("end-date")
    start_date = req.POST.get("start-date")
    activity = req.POST.get("activity")
    current_status_id = req.POST.get("current-status")
    appointment_number = req.POST.get("appointment-number")
    try:
        update_activity_func(
            activity_to_update=activity_to_update,
            end_date=end_date,
            start_date=start_date,
            activity=activity,
            appointment_number=appointment_number,
            current_status_id=current_status_id,
            observations=observations,
        )
        messages.success(req, "Actividad actualizada exitosamente.")
        return activity_page(req, id)

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return activity_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return activity_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return activity_page(req, id)


@login_required
# @audit_manager_required
@selected_audit_required("activities_page")
def activity_total_days_per_month(req: HttpRequest, id: int):
    if req.method != "POST":
        raise Http404

    try:
        activity_to_update = get_object_or_404(
            Activity, pk=id, created_by=req.user, audit__audit_manager=req.user
        )

        for field_name in req.POST:
            if not field_name.startswith("month-"):
                continue

            month, year = field_name.split("&")
            year_id = year.split("-")[1]
            month_id = month.split("-")[1]

            total_days = req.POST.get(field_name)

            update_activity_total_worked_days(
                activity_to_update=activity_to_update,
                month_id=month_id,
                total_days=total_days,
                year_id=year_id,
            )

        messages.success(req, "Días totales trabajados actualizados exitosamente.")
        return redirect("activity", id=activity_to_update.id)

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("activity", id=activity_to_update.id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("activity", id=activity_to_update.id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("activity", id=activity_to_update.id)


@login_required
def update_summary_hours_worked(req: HttpRequest, id: int):
    month = req.POST.get("month")
    total_scheduled_hours = req.POST.get("scheduled-hours")
    total_hours_worked = req.POST.get("worked-hours")
    observations = req.POST.get("observations")

    summary_hours_worked_to_update = get_object_or_404(
        SummaryHoursWorked, pk=id, auditor=req.user
    )
    try:
        update_summary_hours_worked_func(
            summary_hours_worked_to_update=summary_hours_worked_to_update,
            total_scheduled_hours=total_scheduled_hours,
            total_hours_worked=total_hours_worked,
            observations=observations,
            month=month,
        )
        messages.success(req, "Resumen de horas trabajadas actualizado exitosamente.")
        return summary_hours_worked_page(req, id)

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return summary_hours_worked_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return summary_hours_worked_page(req, id)
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return summary_hours_worked_page(req, id)


@login_required
def update_status_of_work_papers(req: HttpRequest, id: int):
    current_status = req.POST.get("current-status")
    end_date = req.POST.get("end-date")
    start_date = req.POST.get("start-date")
    working_papers = req.POST.get("working-papers")
    reference = req.POST.get("reference")
    observations = req.POST.get("observations")

    status_of_work_papers_to_update = get_object_or_404(
        WorkingPapersStatus, pk=id, auditor=req.user
    )
    try:
        update_status_of_work_papers_func(
            status_of_work_papers_to_update=status_of_work_papers_to_update,
            current_status=current_status,
            end_date=end_date,
            start_date=start_date,
            working_papers=working_papers,
            reference=reference,
            observations=observations,
        )

        messages.success(req, "Estado de Papeles de Trabajo actualizado exitosamente.")
        return status_of_work_papers_page(req, id)

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return status_of_work_papers_page(req, id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return status_of_work_papers_page(req, id)

        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return status_of_work_papers_page(req, id)


# Views backend de borrar
@login_required
def delete_audit_time_summary(req: HttpRequest, id: int):
    audit_time_summary = get_object_or_404(AuditTimeSummary, pk=id, auditor=req.user)
    try:
        delete_audit_time_summary_func(audit_time_summary)
        messages.success(req, "Resumen de tiempo de Auditoría eliminado exitosamente.")
        return redirect("audit_time_summary_table")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("audit_time_summary_table")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("audit_time_summary_table")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("audit_time_summary_table")


@login_required
# @superuser_required
def delete_audit_mark(req: HttpRequest, id: int):
    audit_mark_to_delete = get_object_or_404(AuditMarks, pk=id)
    try:
        delete_audit_mark_func(audit_mark_to_delete)
        messages.success(req, "Marca de Auditoría eliminada exitosamente.")
        return redirect("audit_marks")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("audit_marks")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("audit_marks")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("audit_marks")


@login_required
# @superuser_required
def delete_currency_type(req: HttpRequest, id: int):
    currency_type_to_delete = get_object_or_404(CurrencyType, pk=id)
    try:
        delete_currency_type_func(currency_type_to_delete=currency_type_to_delete)
        messages.success(req, "Tipo de moneda eliminado exitosamente.")
        return redirect("currency_types")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("currency_types")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("currency_types")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("currency_types")


@login_required
# @audit_manager_required
@selected_audit_required("activities_page")
def delete_activity(req: HttpRequest, id: int):
    activity_to_delete = get_object_or_404(
        Activity, pk=id, created_by=req.user, audit__audit_manager=req.user
    )
    try:
        delete_activity_func(activity_to_delete)
        messages.success(req, "Actividad eliminada exitosamente.")
        return redirect("activities_page")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("activities_page")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("activities_page")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("activities_page")


@login_required
def delete_status_of_work_papers(req: HttpRequest, id: int):
    status_of_work_papers_to_delete = get_object_or_404(
        WorkingPapersStatus, pk=id, auditor=req.user
    )
    try:
        delete_status_of_work_papers_func(status_of_work_papers_to_delete)
        messages.success(req, "Estado de Papeles de Trabajo eliminado exitosamente.")
        return redirect("status_of_work_papers_table")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("status_of_work_papers_table")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("status_of_work_papers_table")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("status_of_work_papers_table")


@login_required
def delete_summary_hours_worked(req: HttpRequest, id: int):
    summary_hours_worked_to_delete = get_object_or_404(
        SummaryHoursWorked, pk=id, auditor=req.user
    )
    try:
        delete_summary_hours_worked_func(summary_hours_worked_to_delete)
        messages.success(req, "Resumen de Horas Trabajadas eliminado exitosamente.")
        return redirect("summary_worked_hours_table")

    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("summary_worked_hours_table")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, REPORT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("summary_worked_hours_table")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("summary_worked_hours_table")


# Tables Pages
@login_required
@selected_audit_required("audit_time_summary_index")
def audit_time_summary_table_page(req: HttpRequest):
    search_query = req.GET.get("q", "")
    data = {}
    selected_audit: AuditType = req.session.get("selected_audit")
    if not selected_audit:
        return audit_time_summary_index(req)

    if req.GET.get("generate_pdf") == "true":
        # Aquí obtenemos la tabla base, solo con los datos esenciales para la impresión
        table = get_table_to_pdf(
            req,
            AuditTimeSummary,
            BaseAuditTimeSummaryTable,
            selected_audit=selected_audit,
        )

        data["table"] = table

        # Generamos el PDF
        template = get_template("tools/audit-time-summaries_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"resumen_de_tiempo_de_auditorías.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res
    else:
        # Aquí se tienen que pasar la request, el texto que ingresó el usuario para buscar, el modelo y el modelo de la tabla, luego se pasa una tupla los elementos que servirán para filtrarse, tienen que ser campos del primer modelo y, en caso de que sean relaciones, se tienen que pasar como tuplas adentro de la tupla con el campo de relación y el campo de la relación, en caso de que ese campo de relación que se busca también tenga como campo que se busca una relación solo se pone __ para indicar el campo. Luego se pasa la ruta para eliminar una fila, luego la ruta para ver los detalles de una fila, luego se pasa la auditoría seleccionada y de último se pasa el campo de confirmación que tendrá que ingresar el usuario a la hora de eliminar una fila, para asegurar. Opcionalmente se puede pasar un campo de tipo Literal['days', 'seconds', 'minutes', 'hours'] el cual servirá para mostrar el campo fecha o tiempo (si es el que el modelo de tabla lo tiene).
        table = get_table(
            req=req,
            search_query=search_query,
            Model=AuditTimeSummary,
            TableClass=AuditTimeSummaryTable,
            filters=(
                "appointment_number",
                ("assigned_auditor", "role__name"),
                ("assigned_auditor", "first_name"),
                ("assigned_auditor", "last_name"),
            ),
            delete_url="delete_audit_time_summary",
            edit_url="audit_time_summary",
            selected_audit=selected_audit,
            confirmation_field="appointment_number",
        )
        data["table"] = table

    return render(req, "tools/audit-time-summary.html", data)


@login_required
def audit_marks_page(req: HttpRequest):
    search_query = req.GET.get("q", "")
    data = {"request": req}
    if req.GET.get("generate_pdf") == "true":
        table = get_table_to_pdf(
            req,
            AuditMarks,
            BaseAuditMarksTable,
        )

        data["table"] = table

        # Generamos el PDF
        template = get_template("tools/audit-marks_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"marcas-de-auditoría.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res

    table = get_table(
        req=req,
        search_query=search_query,
        Model=AuditMarks,
        TableClass=AuditMarksTable if req.user.is_superuser else BaseAuditMarksTable,
        filters=("name",),
        confirmation_field="name" if req.user.is_superuser else None,
        delete_url="delete_audit_mark" if req.user.is_superuser else None,
        edit_url="audit_mark" if req.user.is_superuser else None,
    )
    context = {"table": table}
    return render(req, "tools/audit-marks-page.html", context)


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

        res = HttpResponse(content_type="application/pdf")
        filename = f"tipos-de-moneda.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res

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


@login_required
@selected_audit_required
def activities_page(req: HttpRequest):
    search_query = req.GET.get("q", "")
    context = {"request": req}

    if req.GET.get("generate_pdf") == "true":
        table = get_table_to_pdf(
            req,
            Activity,
            BaseActivitiesTable,
        )

        context["table"] = table

        # Generamos el PDF
        template = get_template("tools/activities_pdf.html")
        html_content = template.render(context)

        res = HttpResponse(content_type="application/pdf")
        filename = f"activades.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res

    table = get_table(
        req=req,
        search_query=search_query,
        Model=Activity,
        TableClass=(ActivitiesTable if req.user.is_superuser else BaseActivitiesTable),
        filters=(
            "observations",
            "activity",
            "current_status__name",
            "created_by__first_name",
            "created_by__last_name",
            "appointment_number",
            "reference",
        ),
        confirmation_field="activity" if req.user.is_superuser else None,
        delete_url="delete_activity" if req.user.is_superuser else None,
        edit_url="activity" if req.user.is_superuser else None,
    )
    context = {"table": table}
    return render(req, "tools/activities-page.html", context)


@login_required
@selected_audit_required("audit_time_summary_index")
def summary_hours_worked_table_page(req: HttpRequest):
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

        res = HttpResponse(content_type="application/pdf")
        filename = f"resumen_de_tiempo_de_auditorías.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res
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
@selected_audit_required("audit_time_summary_index")
def status_of_work_papers_table_page(req: HttpRequest):
    search_query = req.GET.get("q", "")
    # Se le pasan los parámetros para que pueda generar la tabla, los últimos son las columnas que pueden usarse para buscar en el input de búsqueda
    selected_audit: AuditType = req.session.get("selected_audit")
    data = {}
    if req.GET.get("generate_pdf") == "true":
        # Aquí obtenemos la tabla base, solo con los datos esenciales para la impresión
        table = get_table_to_pdf(
            req,
            WorkingPapersStatus,
            BaseWorkingPapersStatusesTable,
            selected_audit=selected_audit,
        )

        data["table"] = table

        # Generamos el PDF
        template = get_template("tools/summaries-hours-worked_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"resumen_de_tiempo_de_auditorías.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res
    else:
        table = get_table(
            req=req,
            search_query=search_query,
            Model=WorkingPapersStatus,
            TableClass=WorkingPapersStatusesTable,
            filters=("current_status__name", "working_papers", "reference"),
            delete_url="delete_status_of_work_papers",
            edit_url="status_of_work_papers",
            selected_audit=selected_audit,
            confirmation_field="working_papers",
        )

        data["table"] = table

    return render(req, "tools/status-of-work-papers.html", data)


# Vistas para crear
@login_required
# @superuser_required
def create_audit_mark_page(req: HttpRequest):
    return render(req, "tools/create-audit-mark.html")


@login_required
# @superuser_required
def create_currency_type_page(req: HttpRequest):
    countries = Country.objects.exclude(id__in=CurrencyType.objects.values("country"))
    context = {"countries": countries}
    return render(req, "tools/create-currency-type.html", context)


@login_required
@selected_audit_required("activities_page")
# @audit_manager_required
def activity_create_page(req: HttpRequest):
    return render(req, "tools/create-activity-page.html")


@login_required
@selected_audit_required("audit_time_summary_index")
def audit_time_summary_create_page(req: HttpRequest):
    selected_audit: AuditType = req.session.get("selected_audit")

    # Obtiene los auditores que ya están asignados en el AuditTimeSummary
    assigned_auditors = AuditTimeSummary.objects.filter(
        audit__id=selected_audit["id"]
    ).values_list("assigned_auditor__id", flat=True)

    # Filtra los auditores asignados que aún no tienen un AuditTimeSummary asociado como assigned_auditor
    auditors_to_select = [
        assigned_auditor
        for assigned_auditor in selected_audit["assigned_users"]
        if assigned_auditor["id"] not in assigned_auditors
    ]

    data = {"auditors_to_select": auditors_to_select}
    return render(req, "tools/create-audit-time-summary.html", data)


@login_required
@selected_audit_required("audit_time_summary_index")
def status_of_work_papers_create_page(req: HttpRequest):
    return render(req, "tools/create-status-of-work-papers.html")


@login_required
@selected_audit_required("audit_time_summary_index")
def summary_hours_worked_create_page(req: HttpRequest):
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
@selected_audit_required("audit_time_summary_index")
def audit_time_summary_page(req: HttpRequest, id: int):
    audit_time_summary = get_object_or_404(AuditTimeSummary, pk=id, auditor=req.user)
    data = {
        "audit_time_summary": audit_time_summary,
    }

    if req.GET.get("generate_pdf") == "true":
        # Generamos el PDF
        template = get_template("tools/audit-time-summary_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"reporte_de_resumen_de_tiempo_de_auditoría-nombramiento_no_{audit_time_summary.appointment_number}.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        # Convertimos el contenido HTML a PDF
        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()  # Corregido el typo aquí

        res.write(pdf_result)
        return res

    data["progress"] = int(
        (audit_time_summary.worked_days / audit_time_summary.scheduled_days) * 100
    )
    return render(req, "tools/audit-time-summary-page.html", data)


@login_required
@superuser_required
def audit_mark_page(req: HttpRequest, id: int):
    audit_mark = get_object_or_404(AuditMarks, pk=id)
    context = {"audit_mark": audit_mark}
    return render(req, "tools/audit-mark-page.html", context)


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
# @audit_manager_required
@selected_audit_required("activities_page")
def activity_page(req: HttpRequest, id: int):
    activity = get_object_or_404(
        Activity, pk=id, created_by=req.user, audit__audit_manager=req.user
    )
    context = {
        "activity": activity,
        "total_days_per_month_list": activity.get_activity_total_days_per_month_list_dict(),
    }
    return render(req, "tools/activity-page.html", context)


@login_required
@selected_audit_required("audit_time_summary_index")
def status_of_work_papers_page(req: HttpRequest, id: int):
    status_of_work_papers = get_object_or_404(
        WorkingPapersStatus, pk=id, auditor=req.user
    )

    data = {"status_of_work_papers": status_of_work_papers}

    if req.GET.get("generate_pdf") == "true":
        # Generamos el PDF
        template = get_template("tools/status-of-work-papers_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"reporte_de_estado_de_papeles_de_trabajo-referencia_{status_of_work_papers.reference}.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        # Convertimos el contenido HTML a PDF
        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()  # Corregido el typo aquí

        res.write(pdf_result)
        return res

    time_line = get_working_papers_time_line_dic(
        status_of_work_papers.current_status.name
    )
    data["time_line"] = time_line
    return render(req, "tools/status-of-work-papers-page.html", data)


@login_required
@selected_audit_required("audit_time_summary_index")
def summary_hours_worked_page(req: HttpRequest, id: int):
    summary_hours_worked = get_object_or_404(
        SummaryHoursWorked, pk=id, auditor=req.user
    )

    data = {
        "summary_hours_worked": summary_hours_worked,
    }

    if req.GET.get("generate_pdf") == "true":
        # Generamos el PDF
        template = get_template("tools/summary-hours-worked_pdf.html")
        html_content = template.render(data)

        res = HttpResponse(content_type="application/pdf")
        filename = f"reporte_de_resumen_de_horas_trabajadas_del_mes-{summary_hours_worked.month.name.lower()}.pdf"
        res["Content-Disposition"] = f"attachment; filename={filename}"

        html = HTML(string=html_content, base_url=req.build_absolute_uri("/"))
        pdf_result = html.write_pdf()

        res.write(pdf_result)
        return res

    data["progress"] = int(
        (
            summary_hours_worked.total_hours_worked
            / summary_hours_worked.total_scheduled_hours
        )
        * 100
    )
    data["months"] = [
        {"id": month.pk, "name": month.name} for month in Months.objects.all()
    ]

    return render(req, "tools/summary-hours-worked-page.html", data)
