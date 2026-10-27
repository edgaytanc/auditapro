from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from audits.decorators import group_admin_required
from audits.models import Audit
from audits.services import assign_audit_to_user
from tools.models import SummaryHoursWorked

from .const import MANAGEMENT_AUDITORS_ERROR_INSTANCES
from .forms import (
    AuditorCreationForm,
    AuditorRoleUpdateForm,
)
from .services import get_user_to_manage
from django.db.models.deletion import ProtectedError


User = get_user_model()


def _duration_to_hours(duration):
    """
    Convierte un timedelta de Django a horas decimales.
    """

    if not duration:
        return 0

    hours = duration.total_seconds() / 3600

    if hours.is_integer():
        return int(hours)

    return round(hours, 1)


def _get_max_users(user):
    """
    Obtiene el cupo máximo de integrantes del equipo.

    El cupo solamente aplica para usuarios en modalidad grupal.
    El mínimo permitido es de tres integrantes.
    """

    if getattr(user, "modalidad", None) != "G":
        return 0

    max_users = (
        getattr(user, "auditor_slots", None)
        or 3
    )

    if max_users < 3:
        max_users = 3

    return max_users


def _get_team_user_or_404(
    manager_user,
    user_id,
):
    """
    Obtiene un integrante que pertenece al jefe autenticado.

    Si el usuario no existe o pertenece a otro equipo,
    responde con un error 404.
    """

    try:
        return get_user_to_manage(
            manager_user.id,
            user_id,
        )

    except Exception as error:
        raise Http404(
            "El usuario no existe o no pertenece a este equipo."
        ) from error


@login_required
@group_admin_required
def manage_auditors_page(req):
    """
    Alias utilizado por urls.py para mostrar
    el listado de integrantes del equipo.
    """

    return manage_auditors(req)


@login_required
@group_admin_required
def manage_auditors(req):
    """
    Muestra los integrantes asociados al Jefe de Auditoría,
    sus asignaciones, disponibilidad y horas del mes.
    """

    users_qs = (
        User.objects
        .filter(
            administrador=req.user,
            is_deleted=False,
        )
        .select_related("role")
        .order_by(
            "first_name",
            "last_name",
            "id",
        )
    )

    user_count = users_qs.count()
    max_users = _get_max_users(req.user)

    can_add_more_users = (
        user_count < max_users
    )

    now = timezone.now()
    current_year = now.year
    current_month = now.month

    auditor_cards = []

    users_with_assignments = 0
    available_users = 0

    for auditor in users_qs:
        active_audits = (
            Audit.objects
            .filter(
                audit_manager=req.user,
                assigned_users=auditor,
                fechaEnd__gte=now,
            )
            .distinct()
        )

        active_assignments = (
            active_audits.count()
        )

        total_assignments = (
            Audit.objects
            .filter(
                audit_manager=req.user,
                assigned_users=auditor,
            )
            .distinct()
            .count()
        )

        if active_assignments > 0:
            users_with_assignments += 1
            availability_status = "assigned"
            availability_label = "Con asignación"

        else:
            available_users += 1
            availability_status = "available"
            availability_label = "Disponible"

        monthly_hours = (
            SummaryHoursWorked.objects
            .filter(
                auditor=auditor,
                created_at__year=current_year,
                created_at__month=current_month,
            )
            .aggregate(
                worked=Sum(
                    "total_hours_worked"
                ),
                scheduled=Sum(
                    "total_scheduled_hours"
                ),
            )
        )

        worked_hours = _duration_to_hours(
            monthly_hours["worked"]
        )

        scheduled_hours = _duration_to_hours(
            monthly_hours["scheduled"]
        )

        if scheduled_hours > 0:
            performance = round(
                (
                    worked_hours
                    / scheduled_hours
                )
                * 100
            )

            performance = min(
                performance,
                100,
            )

            performance_display = (
                f"{performance}%"
            )

        else:
            performance = 0
            performance_display = "Sin datos"

        full_name = (
            auditor.get_full_name()
            or auditor.username
        )

        initials_parts = [
            part[0].upper()
            for part in full_name.split()
            if part
        ]

        initials = (
            "".join(initials_parts[:2])
            or "AU"
        )

        role_label = (
            auditor.role.verbose_name
            if auditor.role
            else "Sin rol"
        )

        auditor_cards.append(
            {
                "user": auditor,
                "full_name": full_name,
                "initials": initials,
                "role_label": role_label,
                "availability_status": (
                    availability_status
                ),
                "availability_label": (
                    availability_label
                ),
                "active_assignments": (
                    active_assignments
                ),
                "total_assignments": (
                    total_assignments
                ),
                "worked_hours": worked_hours,
                "scheduled_hours": (
                    scheduled_hours
                ),
                "performance": performance,
                "performance_display": (
                    performance_display
                ),
            }
        )

    team_hours = (
        SummaryHoursWorked.objects
        .filter(
            auditor__in=users_qs,
            created_at__year=current_year,
            created_at__month=current_month,
        )
        .aggregate(
            total=Sum(
                "total_hours_worked"
            )
        )
    )

    executed_hours = _duration_to_hours(
        team_hours["total"]
    )

    context = {
        "users_to_manage": users_qs,
        "users": users_qs,
        "auditor_cards": auditor_cards,

        "user_count": user_count,
        "current_users": user_count,

        "max_users": max_users,
        "max_auditors": max_users,
        "can_add_more_users": (
            can_add_more_users
        ),

        "active_users": user_count,
        "available_users": available_users,
        "users_with_assignments": (
            users_with_assignments
        ),
        "executed_hours": executed_hours,
    }

    return render(
        req,
        "management_auditors/manage-auditors.html",
        context,
    )


@login_required
@group_admin_required
def add_auditor(req):
    """
    Crea un integrante respetando el cupo
    permitido para el Jefe de Auditoría.
    """

    max_users = _get_max_users(
        req.user
    )

    current_auditors_count = (
        User.objects
        .filter(
            administrador=req.user,
            is_deleted=False,
        )
        .count()
    )

    if current_auditors_count >= max_users:
        messages.error(
            req,
            (
                "No puedes añadir más usuarios. "
                "Has alcanzado el límite de "
                f"{max_users} usuarios."
            ),
        )

        return redirect(
            "manage_auditors"
        )

    if req.method == "POST":
        form = AuditorCreationForm(
            req.POST
        )

        if form.is_valid():
            created_user = form.save(
                admin_user=req.user
            )

            display_name = (
                created_user.get_full_name()
                or created_user.username
            )

            messages.success(
                req,
                (
                    f"{display_name} fue creado "
                    f"con el rol "
                    f"{created_user.role.verbose_name}."
                ),
            )

            return redirect(
                "manage_auditors"
            )

    else:
        form = AuditorCreationForm()

    return render(
        req,
        "management_auditors/add_auditor.html",
        {
            "form": form,
        },
    )


@login_required
@group_admin_required
def manage_auditor_page(
    req,
    user_id,
):
    """
    Muestra la ficha individual de un integrante,
    sus auditorías, horas, rol y opciones de retiro.
    """

    user_to_manage = (
        _get_team_user_or_404(
            req.user,
            user_id,
        )
    )

    now = timezone.now()

    assigned_audits = (
        Audit.objects
        .filter(
            audit_manager=req.user,
            assigned_users=user_to_manage,
        )
        .distinct()
        .order_by(
            "-fechaEnd",
            "-id",
        )
    )

    available_audits = (
        Audit.objects
        .filter(
            audit_manager=req.user,
        )
        .exclude(
            assigned_users=user_to_manage,
        )
        .distinct()
        .order_by(
            "-fechaEnd",
            "-id",
        )
    )

    active_assignments = (
        assigned_audits
        .filter(
            fechaEnd__gte=now,
        )
        .count()
    )
    
    historical_assignments = (
    assigned_audits.count()
    )

    hours_records_count = (
        SummaryHoursWorked.objects
        .filter(
            auditor=user_to_manage,
        )
        .count()
    )

    can_hard_delete_auditor = (
        historical_assignments == 0
        and hours_records_count == 0
    )

    monthly_hours = (
        SummaryHoursWorked.objects
        .filter(
            auditor=user_to_manage,
            created_at__year=now.year,
            created_at__month=now.month,
        )
        .aggregate(
            worked=Sum(
                "total_hours_worked"
            ),
            scheduled=Sum(
                "total_scheduled_hours"
            ),
        )
    )

    worked_hours = _duration_to_hours(
        monthly_hours["worked"]
    )

    scheduled_hours = _duration_to_hours(
        monthly_hours["scheduled"]
    )

    if scheduled_hours > 0:
        performance = round(
            (
                worked_hours
                / scheduled_hours
            )
            * 100
        )

        performance = min(
            performance,
            100,
        )

        performance_display = (
            f"{performance}%"
        )

    else:
        performance = 0
        performance_display = "Sin datos"

    full_name = (
        user_to_manage.get_full_name()
        or user_to_manage.username
    )

    current_role_name = (
        user_to_manage.role.name
        if user_to_manage.role
        else "auditor"
    )

    context = {
        "user_to_manage": user_to_manage,
        "full_name": full_name,

        # Compatibilidad con la plantilla anterior
        "audits": assigned_audits,

        # Información de auditorías
        "assigned_audits": assigned_audits,
        "available_audits": available_audits,

        "total_assignments": (
            assigned_audits.count()
        ),
        "active_assignments": (
            active_assignments
        ),
        "available_assignments": (
            available_audits.count()
        ),

        # Información de horas y desempeño
        "worked_hours": worked_hours,
        "scheduled_hours": scheduled_hours,
        "performance": performance,
        "performance_display": (
            performance_display
        ),

        # Administración de rol
        "role_form": AuditorRoleUpdateForm(
            initial={
                "system_role": (
                    current_role_name
                ),
            }
        ),

        # Solamente puede retirarse cuando
        # no tiene auditorías activas
        "can_delete_auditor": (
            active_assignments == 0
        ),
        
        "historical_assignments": historical_assignments,
        "hours_records_count": hours_records_count,
        "can_hard_delete_auditor": can_hard_delete_auditor,
        
    }

    return render(
        req,
        "management_auditors/manage-auditor.html",
        context,
    )


@login_required
@group_admin_required
@require_POST
def assign_audit(
    req,
    user_id,
):
    """
    Asigna una o varias auditorías al integrante seleccionado.
    """

    # Verifica que el usuario pertenece al equipo
    _get_team_user_or_404(
        req.user,
        user_id,
    )

    audits_ids = req.POST.getlist(
        "audits_ids"
    )

    try:
        assign_audit_to_user(
            user_id,
            audits_ids,
            req.user.id,
        )

        messages.success(
            req,
            (
                "Las auditorías fueron asignadas "
                "correctamente."
            ),
        )

    except ValueError:
        messages.error(
            req,
            (
                "Alguno de los valores ingresados "
                "no es válido."
            ),
        )

    except Exception as error:
        if isinstance(
            error,
            MANAGEMENT_AUDITORS_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                str(error),
            )

        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado "
                    "al asignar las auditorías."
                ),
            )

    return redirect(
        "manage_auditor",
        user_id=user_id,
    )


@login_required
@group_admin_required
@require_POST
def update_auditor_role(
    req,
    user_id,
):
    """
    Cambia el rol de un integrante perteneciente
    al equipo del Jefe de Auditoría autenticado.
    """

    user_to_manage = (
        _get_team_user_or_404(
            req.user,
            user_id,
        )
    )

    if user_to_manage.is_deleted:
        messages.error(
            req,
            (
                "No se puede modificar el rol "
                "de un usuario retirado."
            ),
        )

        return redirect(
            "manage_auditors"
        )

    form = AuditorRoleUpdateForm(
        req.POST
    )

    if not form.is_valid():
        messages.error(
            req,
            "Selecciona un rol válido.",
        )

        return redirect(
            "manage_auditor",
            user_id=user_id,
        )

    previous_role = (
        user_to_manage.role.verbose_name
        if user_to_manage.role
        else "Sin rol"
    )

    updated_user = form.save(
        user=user_to_manage
    )

    display_name = (
        updated_user.get_full_name()
        or updated_user.username
    )

    messages.success(
        req,
        (
            f"El rol de {display_name} cambió "
            f"de {previous_role} a "
            f"{updated_user.role.verbose_name}."
        ),
    )

    return redirect(
        "manage_auditor",
        user_id=user_id,
    )


@login_required
@group_admin_required
@require_POST
def delete_auditor(
    req,
    user_id,
):
    """
    Retira lógicamente a un integrante del equipo.

    No se elimina físicamente para conservar
    auditorías, horas e historial.
    """

    user_to_manage = (
        _get_team_user_or_404(
            req.user,
            user_id,
        )
    )

    if user_to_manage.is_deleted:
        messages.info(
            req,
            "El usuario ya había sido retirado.",
        )

        return redirect(
            "manage_auditors"
        )

    active_audits_count = (
        Audit.objects
        .filter(
            audit_manager=req.user,
            assigned_users=user_to_manage,
            fechaEnd__gte=timezone.now(),
        )
        .distinct()
        .count()
    )

    if active_audits_count > 0:
        messages.error(
            req,
            (
                "No puedes retirar este usuario "
                "porque tiene "
                f"{active_audits_count} "
                "auditoría(s) activa(s). "
                "Primero debes retirarlo de "
                "esos encargos."
            ),
        )

        return redirect(
            "manage_auditor",
            user_id=user_id,
        )

    display_name = (
        user_to_manage.get_full_name()
        or user_to_manage.username
    )

    with transaction.atomic():
        user_to_manage.is_deleted = True
        user_to_manage.is_active = False
        user_to_manage.deleted_at = (
            timezone.now()
        )

        user_to_manage.save(
            update_fields=[
                "is_deleted",
                "is_active",
                "deleted_at",
            ]
        )

    messages.success(
        req,
        (
            f"{display_name} fue retirado "
            "del equipo. Su historial "
            "se conservó correctamente."
        ),
    )

    return redirect(
        "manage_auditors"
    )
    
@login_required
@group_admin_required
@require_POST
def hard_delete_auditor(
    req,
    user_id,
):
    """
    Elimina permanentemente un integrante únicamente
    cuando no tiene auditorías ni horas registradas.
    """

    user_to_manage = (
        _get_team_user_or_404(
            req.user,
            user_id,
        )
    )

    historical_audits_count = (
        Audit.objects
        .filter(
            assigned_users=user_to_manage,
        )
        .distinct()
        .count()
    )

    hours_records_count = (
        SummaryHoursWorked.objects
        .filter(
            auditor=user_to_manage,
        )
        .count()
    )

    if (
        historical_audits_count > 0
        or hours_records_count > 0
    ):
        messages.error(
            req,
            (
                "Este usuario no puede eliminarse permanentemente "
                "porque tiene información histórica. "
                "Utiliza Retirar del equipo."
            ),
        )

        return redirect(
            "manage_auditor",
            user_id=user_id,
        )

    display_name = (
        user_to_manage.get_full_name()
        or user_to_manage.username
    )

    try:
        with transaction.atomic():
            user_to_manage.delete()

    except ProtectedError:
        messages.error(
            req,
            (
                "No fue posible eliminar el usuario porque existen "
                "otros registros protegidos relacionados con él."
            ),
        )

        return redirect(
            "manage_auditor",
            user_id=user_id,
        )

    messages.success(
        req,
        (
            f"{display_name} fue eliminado permanentemente "
            "de la base de datos."
        ),
    )

    return redirect(
        "manage_auditors"
    )