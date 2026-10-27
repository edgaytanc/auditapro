from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import (
    Http404,
    HttpResponseRedirect,
)
from django.shortcuts import render, redirect
from django.urls import reverse

from audits.access import (
    get_audit_for_user_or_404,
    get_team_owner,
    user_can_access_audit_type,
)
from audits.models import Audit
from audits.utils import audit_to_dict
from users.permissions import (
    has_module_permission,
    is_team_manager,
    module_permission_required,
)

from .models import (
    InternalAuditListOverride,
    InternalAuditControl,
    InternalAuditFinding,
    InternalAuditPlan,
    InternalAuditRisk,
)
from .services import ensure_internal_audit_defaults


def _internal_audits_for_user(
    user,
):
    """
    Retorna únicamente las auditorías internas
    a las que el usuario tiene acceso.
    """

    if not user_can_access_audit_type(user, "I"):
        return Audit.objects.none()

    queryset = (
        Audit.objects
        .filter(
            Q(activa_interna=True)
            | Q(
                activa_financiera=False,
                activa_revisoria=False,
                activa_interna=False,
                tipoAuditoria="I",
            )
        )
        .select_related(
            "audit_manager",
            "audit_manager__role",
        )
        .prefetch_related(
            "assigned_users",
        )
        .distinct()
        .order_by(
            "-created_at",
        )
    )

    if (
        user.is_superuser
        or user.is_staff
    ):
        return queryset

    if is_team_manager(
        user
    ):
        return queryset.filter(
            audit_manager=user,
        )

    team_owner = get_team_owner(
        user
    )

    if team_owner is None:
        return Audit.objects.none()

    return (
        queryset
        .filter(
            audit_manager=team_owner,
            assigned_users=user,
        )
        .distinct()
    )


def _validate_internal_audit(
    audit,
):
    """
    Impide abrir una auditoría que no tenga
    habilitado el flujo de Auditoría Interna.
    """

    if (
        "I"
        not in audit.get_active_type_codes()
    ):
        raise Http404(
            (
                "La auditoría solicitada no tiene "
                "habilitado el módulo interno."
            )
        )


def _parse_optional_date(
    value,
):
    """
    Convierte un valor YYYY-MM-DD en date.
    """

    value = (
        value
        or ""
    ).strip()

    if not value:
        return None

    try:
        return date.fromisoformat(
            value
        )

    except ValueError as error:
        raise ValueError(
            "La fecha ingresada no es válida."
        ) from error


def _redirect_to_internal_tab(
    audit_id,
    tab_name,
):
    """
    Regresa al detalle conservando la pestaña activa.
    """

    url = reverse(
        "internal_audit_detail",
        args=[
            audit_id,
        ],
    )

    return HttpResponseRedirect(
        f"{url}#{tab_name}"
    )


def _internal_user_name(user):
    """
    Retorna el nombre visible de un usuario.
    """

    if user is None:
        return ""

    full_name = (
        user.get_full_name().strip()
        if hasattr(user, "get_full_name")
        else ""
    )

    return (
        full_name
        or getattr(user, "username", "")
        or getattr(user, "email", "")
    )


def _internal_audit_list_row(audit):
    """
    Construye una fila del listado de Auditoría Interna.

    Reglas:
    - Estado y riesgo vienen de Audit.
    - Auditores vienen de assigned_users.
    - Avance se calcula desde Cronograma.
    - Cierre usa Planificación y, como respaldo,
      la fecha final del encargo.
    """

    try:
        plan = audit.internal_plan
    except InternalAuditPlan.DoesNotExist:
        plan = None

    phases = list(
        audit.internal_schedule_phases.all()
    )

    phase_progress = [
        phase.calculated_progress
        for phase in phases
    ]

    progress = (
        round(
            sum(phase_progress)
            / len(phase_progress)
        )
        if phase_progress
        else 0
    )

    close_date = None

    if (
        plan
        and plan.estimated_end_date
    ):
        close_date = (
            plan.estimated_end_date
        )

    elif audit.fechaEnd:
        close_date = (
            audit.fechaEnd.date()
        )

    days_to_close = (
        (
            close_date
            - date.today()
        ).days
        if close_date
        else None
    )

    status_slug = (
        audit.workflow_status
        or "planning"
    )

    status_label = dict(
        Audit.STATUS_CHOICES
    ).get(
        status_slug,
        "Planificación",
    )

    risk_slug = (
        audit.risk_level
        or "undefined"
    )

    risk_label = dict(
        Audit.RISK_CHOICES
    ).get(
        risk_slug,
        "Sin definir",
    )

    auditor_names = []

    for user in audit.assigned_users.all():
        user_name = _internal_user_name(
            user
        )

        if user_name:
            auditor_names.append(
                user_name
            )

    auditor_display = (
        ", ".join(auditor_names)
        if auditor_names
        else "Sin asignar"
    )

    code_year = (
        audit.created_at.year
        if audit.created_at
        else date.today().year
    )

    # La captura manual es un complemento del encargo, no modifica sus
    # campos usados por otros módulos ni el cálculo de cronograma.
    try:
        override = audit.internal_list_override
    except InternalAuditListOverride.DoesNotExist:
        override = None

    if override:
        if override.display_code:
            code = override.display_code
        else:
            code = f"AI-{code_year}-{str(audit.id).zfill(3)}"
        process_area = override.process_area or audit.title or "Sin definir"
        client_name = override.client or audit.identidad or "Sin definir"
        auditor_display = override.auditor_name or auditor_display
        progress = (override.manual_progress if override.manual_progress is not None else progress)
        close_date = override.manual_close_date or close_date
        status_slug = override.manual_status or status_slug
        risk_slug = override.manual_risk or risk_slug
        status_label = dict(Audit.STATUS_CHOICES).get(status_slug, "Planificación")
        risk_label = dict(Audit.RISK_CHOICES).get(risk_slug, "Sin definir")
        days_to_close = (close_date - date.today()).days if close_date else None
    else:
        code = f"AI-{code_year}-{str(audit.id).zfill(3)}"
        process_area = audit.title or "Sin definir"
        client_name = audit.identidad or "Sin definir"

    return {
        "audit": audit,

        "code": code,

        "process_area": process_area,

        "client": client_name,

        "status_slug": (
            status_slug
        ),

        "status_label": (
            status_label
        ),

        "risk_slug": (
            risk_slug
        ),

        "risk_label": (
            risk_label
        ),

        "auditor_names": (
            auditor_names
        ),

        "auditor_display": (
            auditor_display
        ),

        "progress": (
            progress
        ),

        "close_date": (
            close_date
        ),

        "days_to_close": (
            days_to_close
        ),
    }


@login_required
@module_permission_required(
    "audits",
    "view",
)
def internal_audit_list(
    request,
):
    """
    Listado principal de Auditoría Interna.
    """

    if request.method == "POST" and request.POST.get("list_action") == "clear_row":
        if not has_module_permission(request.user, "audits", "edit"):
            messages.error(request, "No tienes permiso para editar el listado.")
            return redirect("dashboard_interna")
        try:
            audit_id = int(request.POST.get("audit_id", "0"))
            audit = get_audit_for_user_or_404(request.user, audit_id, action="edit", module="audits")
            _validate_internal_audit(audit)
            if not user_can_access_audit_type(request.user, "I"):
                raise Http404("Acceso no autorizado")
            InternalAuditListOverride.objects.filter(audit=audit).delete()
            messages.success(request, "Campos manuales restablecidos. No se eliminó la auditoría.")
        except (ValueError, TypeError):
            messages.error(request, "Auditoría inválida.")
        return redirect("dashboard_interna")

    if request.method == "POST" and request.POST.get("list_action") == "save_row":
        if not has_module_permission(request.user, "audits", "edit"):
            messages.error(request, "No tienes permiso para editar el listado.")
            return redirect("dashboard_interna")
        try:
            audit_id = int(request.POST.get("audit_id", "0"))
            audit = get_audit_for_user_or_404(request.user, audit_id, action="edit", module="audits")
            _validate_internal_audit(audit)
            if not user_can_access_audit_type(request.user, "I"):
                raise Http404("Acceso no autorizado a Auditoría Interna")
            status = request.POST.get("workflow_status", "planning").strip()
            risk = request.POST.get("risk_level", "undefined").strip()
            if status not in dict(Audit.STATUS_CHOICES) or risk not in dict(Audit.RISK_CHOICES):
                raise ValueError("Estado o riesgo inválido")
            percent = int(request.POST.get("manual_progress", "0"))
            if not 0 <= percent <= 100:
                raise ValueError("El avance debe estar entre 0 y 100")
            close_date = _parse_optional_date(request.POST.get("manual_close_date"))
            values = {
                "display_code": request.POST.get("display_code", "").strip()[:60],
                "process_area": request.POST.get("process_area", "").strip()[:255],
                "client": request.POST.get("client", "").strip()[:255],
                "auditor_name": request.POST.get("auditor_name", "").strip()[:255],
                "manual_progress": percent,
                "manual_close_date": close_date,
                "manual_status": status,
                "manual_risk": risk,
            }
            InternalAuditListOverride.objects.update_or_create(audit=audit, defaults=values)
            messages.success(request, "Datos manuales de la auditoría guardados.")
        except (ValueError, TypeError) as exc:
            messages.error(request, str(exc))
        return redirect("dashboard_interna")

    auditorias = (
        _internal_audits_for_user(
            request.user
        )
        .select_related(
            "internal_plan",
            "internal_list_override",
        )
        .prefetch_related(
            "internal_schedule_phases",
        )
    )

    rows = [
        _internal_audit_list_row(
            audit
        )
        for audit in auditorias
    ]

    auditor_filter_options = sorted({
        auditor_name

        for row in rows

        for auditor_name
        in row["auditor_names"]
    })

    context = {
        "audit_rows": rows,

        "auditor_filter_options": (
            auditor_filter_options
        ),

        "can_edit": has_module_permission(request.user, "audits", "edit"),
        "status_choices": Audit.STATUS_CHOICES,
        "risk_choices": Audit.RISK_CHOICES,
        "can_create": (
            has_module_permission(
                request.user,
                "audits",
                "create",
            )
        ),
    }

    return render(
        request,
        "internal_audit/list.html",
        context,
    )

@login_required
@module_permission_required(
    "audits",
    "view",
)
def internal_audit_detail(
    request,
    audit_id,
):
    """
    Ficha principal de la Auditoría Interna.
    """

    audit = (
        get_audit_for_user_or_404(
            request.user,
            audit_id,
            action="view",
            module="audits",
        )
    )

    _validate_internal_audit(audit)
    if not user_can_access_audit_type(request.user, "I"):
        raise Http404("No tienes habilitada Auditoría Interna.")

    request.session[
        "selected_audit"
    ] = audit_to_dict(
        audit
    )

    request.session.modified = True

    internal_data = (
        ensure_internal_audit_defaults(
            request,
            audit,
        )
    )

    plan = internal_data[
        "plan"
    ]

    report = internal_data[
        "report"
    ]

    phases = list(
        internal_data[
            "phases"
        ]
    )

    can_edit = (
        has_module_permission(
            request.user,
            "audits",
            "edit",
        )
    )

    if request.method == "POST":
        detail_action = (
            request.POST.get(
                "detail_action",
                "",
            )
            .strip()
            .lower()
        )

        if not can_edit:
            messages.error(
                request,
                (
                    "No tienes permiso para editar "
                    "esta Auditoría Interna."
                ),
            )

            return _redirect_to_internal_tab(
                audit.id,
                "planificacion",
            )

        # Revalida el acceso de edición.
        get_audit_for_user_or_404(
            request.user,
            audit.id,
            action="edit",
            module="audits",
        )

        if detail_action == "save_plan":
            try:
                budgeted_hours_raw = (
                    request.POST.get(
                        "budgeted_hours",
                        "0",
                    )
                    .strip()
                )

                budgeted_hours = int(
                    budgeted_hours_raw
                    or "0"
                )

                if budgeted_hours < 0:
                    raise ValueError(
                        (
                            "Las horas presupuestadas "
                            "no pueden ser negativas."
                        )
                    )

                plan.client_name = (
                    request.POST.get(
                        "client_name",
                        "",
                    )
                    .strip()
                )

                plan.objective = (
                    request.POST.get(
                        "objective",
                        "",
                    )
                    .strip()
                )

                plan.scope = (
                    request.POST.get(
                        "scope",
                        "",
                    )
                    .strip()
                )

                plan.methodology = (
                    request.POST.get(
                        "methodology",
                        "",
                    )
                    .strip()
                )

                plan.budgeted_hours = (
                    budgeted_hours
                )

                plan.start_date = (
                    _parse_optional_date(
                        request.POST.get(
                            "start_date"
                        )
                    )
                )

                plan.estimated_end_date = (
                    _parse_optional_date(
                        request.POST.get(
                            "estimated_end_date"
                        )
                    )
                )

                plan.assigned_team = (
                    request.POST.get(
                        "assigned_team",
                        "",
                    )
                    .strip()
                )

                plan.updated_by = (
                    request.user
                )

                plan.full_clean()
                plan.save()

                messages.success(
                    request,
                    (
                        "La planificación fue "
                        "guardada correctamente."
                    ),
                )

            except (
                TypeError,
                ValueError,
            ) as error:
                messages.error(
                    request,
                    str(error),
                )

            except Exception as error:
                messages.error(
                    request,
                    (
                        "No fue posible guardar "
                        f"la planificación: {error}"
                    ),
                )

            return _redirect_to_internal_tab(
                audit.id,
                "planificacion",
            )

        if detail_action == "clear_plan":
            plan.client_name = ""
            plan.objective = ""
            plan.scope = ""
            plan.methodology = ""
            plan.budgeted_hours = 0
            plan.start_date = None
            plan.estimated_end_date = None
            plan.assigned_team = ""
            plan.updated_by = request.user

            plan.save(
                update_fields=[
                    "client_name",
                    "objective",
                    "scope",
                    "methodology",
                    "budgeted_hours",
                    "start_date",
                    "estimated_end_date",
                    "assigned_team",
                    "updated_by",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                (
                    "Los datos manuales de "
                    "planificación fueron borrados."
                ),
            )

            return _redirect_to_internal_tab(
                audit.id,
                "planificacion",
            )

        messages.error(
            request,
            "La operación solicitada no es válida.",
        )

        return _redirect_to_internal_tab(
            audit.id,
            "planificacion",
        )

    risks = list(
        InternalAuditRisk.objects
        .filter(
            audit=audit,
        )
        .order_by(
            "sort_order",
            "id",
        )
    )

    controls = list(
        InternalAuditControl.objects
        .filter(
            audit=audit,
        )
        .select_related(
            "risk",
        )
        .order_by(
            "sort_order",
            "id",
        )
    )

    findings = list(
        InternalAuditFinding.objects
        .filter(
            audit=audit,
        )
        .order_by(
            "sort_order",
            "code",
            "id",
        )
    )

    phase_progress_values = [
        phase.calculated_progress
        for phase in phases
    ]

    global_progress = (
        round(
            sum(
                phase_progress_values
            )
            / len(
                phase_progress_values
            )
        )
        if phase_progress_values
        else 0
    )

    close_date = (
        plan.estimated_end_date
    )

    days_to_close = (
        (
            close_date
            - date.today()
        ).days
        if close_date
        else None
    )

    context = {
        "audit": audit,
        "plan": plan,
        "report": report,
        "phases": phases,
        "risks": risks,
        "controls": controls,
        "findings": findings,
        "can_edit": can_edit,

        "global_progress": (
            global_progress
        ),
        "days_to_close": (
            days_to_close
        ),

        "high_residual_count": sum(
            1
            for risk in risks
            if risk.residual_level == "high"
        ),
        "medium_residual_count": sum(
            1
            for risk in risks
            if risk.residual_level == "medium"
        ),
        "low_residual_count": sum(
            1
            for risk in risks
            if risk.residual_level == "low"
        ),

        "effective_controls_count": sum(
            1
            for control in controls
            if (
                control.effectiveness_level
                == "adequate"
            )
        ),
        "pending_controls_count": sum(
            1
            for control in controls
            if (
                control.effectiveness_level
                != "adequate"
            )
        ),

        "significant_findings_count": sum(
            1
            for finding in findings
            if (
                finding.severity
                == "significant"
            )
        ),
        "implemented_findings_count": sum(
            1
            for finding in findings
            if (
                finding.status
                == "implemented"
            )
        ),
        "overdue_findings_count": sum(
            1
            for finding in findings
            if (
                finding.deadline_level
                == "overdue"
            )
        ),
    }

    return render(
        request,
        "internal_audit/detail.html",
        context,
    )