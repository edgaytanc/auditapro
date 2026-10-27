from django.shortcuts import render, get_object_or_404, redirect

from audits.utils import get_assigned_audits
from .decorators import audit_manager_required
from .models import Audit
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import (
    Http404,
    HttpRequest,
    JsonResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from audits.services import (
    unassign_audit as unassign_audit_func,
    delete_audit as delete_audit_func,
    create_audit as create_audit_func,
    client_can_create_audit_type,
    assign_audit as assign_audit_func,
    multiple_assign_audit,
    update_audit,
)
from django.contrib import messages
from .consts import AUDIT_ERROR_INSTANCES
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db import transaction

from users.models import (
    Roles,
    RoleModulePermission,
)
from users.permissions import (
    has_module_permission,
    is_team_manager,
    module_permission_required,
)
from .access import (
    get_team_owner,
    get_audit_for_user_or_404,
)

from django.db.models import (
    Count,
    Q,
)


User = get_user_model()
PERMISSION_ROLE_DEFINITIONS = {
    "auditor": "Auditor",
    "supervisor": "Supervisor",
    "readonly": "Solo Lectura",
}


PERMISSION_PRESETS = {
    "auditor": {
        "audits": {
            "view",
            "create",
            "edit",
        },
        "clients": {
            "view",
            "create",
            "edit",
        },
        "workpapers": {
            "view",
            "create",
            "edit",
        },
        "findings": {
            "view",
            "create",
            "edit",
        },
        "reports": {
            "view",
            "create",
        },
        "users": set(),
    },

    "supervisor": {
        "audits": {
            "view",
        },
        "clients": {
            "view",
        },
        "workpapers": {
            "view",
            "edit",
        },
        "findings": {
            "view",
            "edit",
        },
        "reports": {
            "view",
            "edit",
        },
        "users": set(),
    },

    "readonly": {
        "audits": {
            "view",
        },
        "clients": {
            "view",
        },
        "workpapers": {
            "view",
        },
        "findings": {
            "view",
        },
        "reports": {
            "view",
        },
        "users": set(),
    },
}
def _build_audit_row(audit, now):
    """
    Construye la información visual de una auditoría.

    - Avance y estado utilizan los valores guardados.
    - Si no existen, se estiman mediante las fechas.
    - Riesgo utiliza el valor guardado en la auditoría.
    - Hallazgos utiliza únicamente registros activos.
    """
    def to_local_date(value):
        """
        Convierte un datetime con o sin zona horaria
        en una fecha local comparable.
        """
        if timezone.is_aware(value):
            value = timezone.localtime(value)

        return value.date()

    start_date = to_local_date(audit.fechaInit)
    end_date = to_local_date(audit.fechaEnd)
    current_date = to_local_date(now)

    progress_options = [
        0,
        10,
        25,
        50,
        65,
        75,
        88,
        100,
    ]

    if end_date <= current_date:
        raw_progress = 100
        status_slug = "completed"
        status_label = "Finalizada"

    elif start_date > current_date:
        raw_progress = 0
        status_slug = "planning"
        status_label = "Planificación"

    else:
        total_days = (
            end_date - start_date
        ).days

        elapsed_days = (
            current_date - start_date
        ).days

        if total_days > 0:
            raw_progress = round(
                elapsed_days / total_days * 100
            )
        else:
            raw_progress = 0

        raw_progress = max(
            0,
            min(raw_progress, 100),
        )

        if raw_progress >= 85:
            status_slug = "review"
            status_label = "En Revisión"
        else:
            status_slug = "progress"
            status_label = "En Proceso"

    progress = min(
        progress_options,
        key=lambda value: abs(value - raw_progress),
    )

    # Si ya existen valores guardados manualmente,
    # tienen prioridad sobre la estimación por fechas.
    if audit.progress is not None:
        progress = audit.progress

    if audit.workflow_status:
        status_slug = audit.workflow_status
        status_label = dict(
            Audit.STATUS_CHOICES
        ).get(
            status_slug,
            status_label,
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

    type_information = {
    "F": {
        "label": "Financiera",
        "slug": "financial",
    },
    "R": {
        "label": "Revisoría Fiscal",
        "slug": "fiscal",
    },
    "I": {
        "label": "Auditoría Interna",
        "slug": "internal",
    },
}

    selected_type_codes = (
        audit.get_active_type_codes()
    )

    audit_types = [
        type_information[code]
        for code in selected_type_codes
        if code in type_information
    ]

    if not audit_types:
        audit_types = [
            {
                "label": "Sin definir",
                "slug": "undefined",
            }
        ]

    type_labels = [
        audit_type["label"]
        for audit_type in audit_types
    ]

    type_slugs = [
        audit_type["slug"]
        for audit_type in audit_types
    ]

    manager_name = (
        audit.audit_manager.get_full_name()
        or audit.audit_manager.username
    )

    team = []

    for assigned_user in audit.assigned_users.all():
        full_name = (
            assigned_user.get_full_name()
            or assigned_user.username
        )

        name_parts = [
            part
            for part in full_name.split()
            if part
        ]

        initials = "".join(
            part[0].upper()
            for part in name_parts[:2]
        )

        team.append({
            "id": assigned_user.id,
            "name": full_name,
            "initials": initials or "AU",
        })

    code_year = (
        audit.created_at.year
        if audit.created_at
        else start_date.year
    )

    findings_count = getattr(
        audit,
        "active_findings_count",
        None,
    )

    if findings_count is None:
        findings_count = (
            audit.findings
            .filter(
                is_active=True,
            )
            .count()
        )

    if audit.manual_findings_count is not None:
        findings_count = audit.manual_findings_count

    return {
        "audit": audit,

        "code": (
            f"AUD-{code_year}-"
            f"{str(audit.id).zfill(3)}"
        ),

        "client": audit.identidad,
        "title": audit.title,

        "types": audit_types,

        "type_label": " / ".join(
            type_labels
        ),

        "type_slug": " ".join(
            type_slugs
        ),

        "period": (
            audit.periodo_auditado.strip()
            if audit.periodo_auditado
            else (
                f"{start_date.strftime('%d/%m/%Y')} "
                f"– {end_date.strftime('%d/%m/%Y')}"
            )
        ),

        "manager_name": manager_name,
        "team": team,

        "progress": progress,

        "status_slug": status_slug,
        "status_label": status_label,

        "risk_slug": risk_slug,
        "risk_label": risk_label,

        "findings": findings_count,
    }


@login_required
@audit_manager_required
def role_permissions_matrix(req):
    """
    Matriz de permisos configurable por cada
    Jefe de Auditoría.

    La configuración se almacena por:
    - Jefe propietario
    - Rol
    - Módulo
    """
    role_objects = {}

    for role_name, verbose_name in (
        PERMISSION_ROLE_DEFINITIONS.items()
    ):
        role, _created = Roles.objects.get_or_create(
            name=role_name,
            defaults={
                "verbose_name": verbose_name,
            },
        )

        role_objects[role_name] = role

    requested_role_name = (
        req.POST.get("role_name")
        if req.method == "POST"
        else req.GET.get("role")
    )

    if (
        requested_role_name
        not in PERMISSION_ROLE_DEFINITIONS
    ):
        requested_role_name = "auditor"

    selected_role = role_objects[
        requested_role_name
    ]

    current_permissions = (
        RoleModulePermission.objects
        .filter(
            owner=req.user,
            role=selected_role,
        )
    )

    # La primera vez que se abre un rol,
    # se crea automáticamente su plantilla base.
    if not current_permissions.exists():
        preset = PERMISSION_PRESETS[
            requested_role_name
        ]

        with transaction.atomic():
            for module, _module_label in (
                RoleModulePermission.MODULE_CHOICES
            ):
                allowed_actions = preset.get(
                    module,
                    set(),
                )

                RoleModulePermission.objects.create(
                    owner=req.user,
                    role=selected_role,
                    module=module,
                    can_view=(
                        "view" in allowed_actions
                    ),
                    can_create=(
                        "create" in allowed_actions
                    ),
                    can_edit=(
                        "edit" in allowed_actions
                    ),
                    can_delete=(
                        "delete" in allowed_actions
                    ),
                )

    if req.method == "POST":
        with transaction.atomic():
            for module, _module_label in (
                RoleModulePermission.MODULE_CHOICES
            ):
                RoleModulePermission.objects.update_or_create(
                    owner=req.user,
                    role=selected_role,
                    module=module,
                    defaults={
                        "can_view": (
                            f"permission_{module}_view"
                            in req.POST
                        ),
                        "can_create": (
                            f"permission_{module}_create"
                            in req.POST
                        ),
                        "can_edit": (
                            f"permission_{module}_edit"
                            in req.POST
                        ),
                        "can_delete": (
                            f"permission_{module}_delete"
                            in req.POST
                        ),
                    },
                )

        messages.success(
            req,
            (
                "La matriz de permisos para "
                f"{selected_role.verbose_name} "
                "fue guardada correctamente."
            ),
        )

        return redirect(
            (
                f"{req.path}"
                f"?role={requested_role_name}"
            )
        )

    permission_map = {
        permission.module: permission
        for permission in (
            RoleModulePermission.objects
            .filter(
                owner=req.user,
                role=selected_role,
            )
        )
    }

    permission_rows = []

    for module, module_label in (
        RoleModulePermission.MODULE_CHOICES
    ):
        permission = permission_map.get(
            module
        )

        permission_rows.append({
            "module": module,
            "label": module_label,
            "can_view": (
                permission.can_view
                if permission
                else False
            ),
            "can_create": (
                permission.can_create
                if permission
                else False
            ),
            "can_edit": (
                permission.can_edit
                if permission
                else False
            ),
            "can_delete": (
                permission.can_delete
                if permission
                else False
            ),
        })

    role_options = [
        {
            "name": role_name,
            "label": verbose_name,
        }
        for role_name, verbose_name in (
            PERMISSION_ROLE_DEFINITIONS.items()
        )
    ]

    context = {
        "selected_role_name": (
            requested_role_name
        ),
        "selected_role": selected_role,
        "role_options": role_options,
        "permission_rows": permission_rows,
    }

    return render(
        req,
        "audits/role-permissions-matrix.html",
        context,
    )

@login_required
def assigned_audits(
    req,
):
    """
    Muestra el listado principal de auditorías.
    """

    if req.method == "GET":
        return assigned_audits_page(
            req
        )

    return HttpResponseNotAllowed(
        [
            "GET",
        ]
    )

@login_required
@module_permission_required(
    "audits",
    "create",
)
def create_audit_view(
    req: HttpRequest,
):
    """
    Permite abrir o enviar el formulario de creación
    únicamente cuando el usuario tiene permiso Crear.
    """

    if req.method == "GET":
        return create_audit_page(req)

    if req.method == "POST":
        return create_audit(req)

    return HttpResponseNotAllowed(
        [
            "GET",
            "POST",
        ]
    )

@audit_manager_required
@login_required
def manage_audit_view(req, audit_id):
    if req.method == "GET":
        return manage_audit_page(req, audit_id)
    elif req.method == "POST":
        return manage_audit(req, audit_id)


@audit_manager_required
@login_required
def manage_audit_redirect(req):
    return redirect("assigned_audits")


@login_required
@audit_manager_required
def unassign_audit_view(req, audit_id, user_id):
    if req.method == "GET":
        return unassign_audit_page(req, audit_id, user_id)
    elif req.method == "POST":
        return unassign_audit(req, audit_id, user_id)


@login_required
@require_POST
def delete_audit_view(
    req,
    audit_id,
):
    """
    Elimina una auditoría únicamente cuando el usuario
    tiene acceso a ella y permiso Eliminar.
    """

    try:
        audit = get_audit_for_user_or_404(
            req.user,
            audit_id,
            action="delete",
        )

        delete_audit_func(
            audit.id,
            audit.audit_manager_id,
        )

        messages.success(
            req,
            (
                "La auditoría fue eliminada "
                "correctamente."
            ),
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            AUDIT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )

        else:
            messages.error(
                req,
                (
                    "No fue posible eliminar "
                    "la auditoría."
                ),
            )

    return redirect(
        "assigned_audits"
    )


def create_audit(req):
    """
    Crea una auditoría respetando el equipo y los permisos.

    Si crea el Jefe de Auditoría:
    - La auditoría queda a su nombre.
    - Puede seleccionar integrantes en modalidad grupal.

    Si crea un Auditor o Supervisor:
    - La auditoría queda bajo el Jefe de su equipo.
    - El creador se asigna automáticamente.
    """

    redirect_target = (
        "assigned_audits"
        if req.POST.get(
            "return_to"
        ) == "assigned_audits"
        else "create_audit"
    )

    team_owner = get_team_owner(
        req.user
    )

    if team_owner is None:
        return HttpResponseForbidden(
            (
                "No fue posible identificar "
                "el Jefe de Auditoría de tu equipo."
            )
        )

    audit_title = req.POST.get(
        "audit_title",
        "",
    ).strip()

    audit_identidad = req.POST.get(
        "audit_identidad",
        "",
    ).strip()

    audit_fecha_inicio = req.POST.get(
        "audit_fechaInit"
    )

    audit_fecha_final = req.POST.get(
        "audit_fechaEnd"
    )

    audit_period = req.POST.get(
        "audit_period",
        "",
    ).strip()

    audit_initial_risk = req.POST.get(
        "audit_initial_risk",
        "medium",
    )

    # Los formularios actuales envían un radio nativo F/R/I.
    # Los formularios heredados pueden continuar enviando las tres banderas,
    # siempre que solo una esté marcada. Nunca confiar en el HTML solamente.
    selected_radio = req.POST.get("selected_audit_type")
    legacy_flags = (
        "audit_financial" in req.POST,
        "activa_revisoria" in req.POST,
        "audit_internal" in req.POST,
    )
    if selected_radio is not None:
        if (
            selected_radio not in ("F", "R", "I")
            or len(req.POST.getlist("selected_audit_type")) != 1
            or any(legacy_flags)
        ):
            messages.error(req, "Selecciona exactamente un tipo de auditoría.")
            return redirect(redirect_target)
        audit_financial = selected_radio == "F"
        activa_revisoria = selected_radio == "R"
        audit_internal = selected_radio == "I"
    else:
        audit_financial, activa_revisoria, audit_internal = legacy_flags

    audit_moneda = req.POST.get(
        "audit_moneda"
    )

    selected_count = sum(
        [
            audit_financial,
            activa_revisoria,
            audit_internal,
        ]
    )

    # Validar en el servidor: deshabilitar casillas en HTML no basta.
    if selected_count != 1:
        messages.error(req, "Selecciona exactamente un tipo de auditoría.")
        return redirect(redirect_target)

    selected_type = (
        "F" if audit_financial else "R" if activa_revisoria else "I"
    )
    if not client_can_create_audit_type(team_owner, selected_type):
        messages.error(req, "El cliente no tiene habilitado ese tipo de auditoría.")
        return redirect(redirect_target)

    if not audit_period:
        messages.error(
            req,
            "Ingresa el período auditado.",
        )

        return redirect(
            redirect_target
        )

    requester_is_manager = (
        is_team_manager(
            req.user
        )
    )

    if requester_is_manager:
        if (
            getattr(
                team_owner,
                "modalidad",
                None,
            )
            == "G"
        ):
            audit_assigned_users_ids = (
                req.POST.getlist(
                    "audit_assigned_users_ids"
                )
            )

        else:
            audit_assigned_users_ids = [
                str(team_owner.id)
            ]

    else:
        # Un integrante con permiso Crear no puede
        # enviar IDs arbitrarios. Se asigna a sí mismo.
        audit_assigned_users_ids = [
            str(req.user.id)
        ]

    try:
        created_audit = create_audit_func(
            team_owner,
            audit_title,
            audit_identidad,
            audit_fecha_inicio,
            audit_fecha_final,
            audit_financial,
            activa_revisoria,
            audit_internal,
            audit_period,
            audit_initial_risk,
            audit_moneda,
            audit_assigned_users_ids,
        )

        messages.success(
            req,
            (
                "Auditoría creada correctamente. "
                f"Código interno: {created_audit.id}."
            ),
        )

        return redirect(
            redirect_target
        )

    except ValueError as error:
        messages.error(
            req,
            str(error),
        )

        return redirect(
            redirect_target
        )

    except Exception as error:
        error_message = str(
            error
        )

        if isinstance(
            error,
            AUDIT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )

        else:
            messages.error(
                req,
                (
                    "Ocurrió un error inesperado "
                    "al crear la auditoría."
                ),
            )

        return redirect(
            redirect_target
        )


def create_audit_page(req):
    """
    Renderiza la pantalla independiente de creación.

    La autorización ya fue validada por
    create_audit_view.
    """

    team_owner = get_team_owner(
        req.user
    )

    if team_owner is None:
        return HttpResponseForbidden(
            (
                "No fue posible identificar "
                "el equipo del usuario."
            )
        )

    requester_is_manager = (
        is_team_manager(
            req.user
        )
    )

    show_assignment = (
        requester_is_manager
        and getattr(
            team_owner,
            "modalidad",
            None,
        ) == "G"
    )

    if show_assignment:
        users_to_assign_audits = (
            User.objects
            .filter(
                administrador=team_owner,
                is_deleted=False,
                is_active=True,
            )
            .exclude(
                id=team_owner.id,
            )
            .select_related(
                "role",
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    else:
        users_to_assign_audits = (
            User.objects.none()
        )

    select_options = [
        {
            "option_value": user.id,
            "text_to_show1": (
                user.get_full_name()
                or user.username
            ),
            "text_to_show2": (
                user.role.verbose_name
                if user.role
                else "Sin rol"
            ),
        }
        for user
        in users_to_assign_audits
    ]

    manager_name = (
        team_owner.get_full_name()
        or team_owner.username
    )

    data = {
        "users_to_asiggn_audits": (
            users_to_assign_audits
        ),
        "select_options": select_options,
        "show_assignment": (
            show_assignment
        ),
        "manager_name": manager_name,
        "can_create_revisoria": client_can_create_audit_type(team_owner, "R"),
        "can_create_interna": client_can_create_audit_type(team_owner, "I"),
    }

    return render(
        req,
        "audits/create-audit.html",
        data,
    )

@audit_manager_required
@login_required
def manage_audit(req, audit_id):
    audit_title = req.POST.get(
        "audit_title",
        "",
    )

    audit_identidad = req.POST.get(
        "audit_identidad",
        "",
    )

    audit_fecha_inicio = req.POST.get(
        "audit_fechaInit",
        "",
    )

    audit_fecha_final = req.POST.get(
        "audit_fechaEnd",
        "",
    )

    audit_periodo = req.POST.get(
        "audit_period",
        "",
    )

    audit_moneda = req.POST.get(
        "audit_moneda",
        "GTQ",
    )

    audit_financial = (
        "audit_financial" in req.POST
    )

    activa_revisoria = (
        "activa_revisoria" in req.POST
    )

    audit_internal = (
        "audit_internal" in req.POST
    )

    progress = req.POST.get(
        "progress",
        "0",
    )

    risk_level = req.POST.get(
        "risk_level",
        "undefined",
    )

    workflow_status = req.POST.get(
        "workflow_status",
        "planning",
    )

    if not any([
        audit_financial,
        activa_revisoria,
        audit_internal,
    ]):
        messages.error(
            req,
            "Selecciona al menos un tipo de auditoría.",
        )

        return redirect(
            "manage_audit",
            audit_id,
        )

    try:
        update_audit(
            audit_id=audit_id,
            audit_title=audit_title,
            audit_identidad=audit_identidad,
            audit_fecha_inicio=audit_fecha_inicio,
            audit_fecha_final=audit_fecha_final,
            audit_periodo=audit_periodo,
            audit_moneda=audit_moneda,
            audit_financial=audit_financial,
            activa_revisoria=activa_revisoria,
            audit_internal=audit_internal,
            progress=progress,
            risk_level=risk_level,
            workflow_status=workflow_status,
            audit_manager_id=req.user.id,
        )

        messages.success(
            req,
            "Auditoría modificada exitosamente.",
        )

    except ValueError as error:
        messages.error(
            req,
            str(error),
        )

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            AUDIT_ERROR_INSTANCES,
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
        "manage_audit",
        audit_id,
    )

@audit_manager_required
@login_required
def assign_audit(req, audit_id, user_id):
    try:
        assign_audit_func(audit_id, user_id, req.user.id)
        messages.success(
            req, "La Auditoría fue asignada a el usuario seleccionado exitosamente."
        )
        return redirect("manage_audit", audit_id)
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("manage_audit", audit_id)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, AUDIT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("manage_audit", audit_id)
        else:
            messages.error(req, error_message)
            return redirect("manage_audit", audit_id)


@login_required
@audit_manager_required
def manage_audit_assign_audit(req, audit_id):
    """
    Asigna uno o varios miembros del equipo
    a una auditoría administrada por el usuario.
    """
    if req.method != "POST":
        return redirect(
            "manage_audit",
            audit_id,
        )

    audit = get_object_or_404(
        Audit,
        pk=audit_id,
        audit_manager=req.user,
    )

    requested_ids = {
        str(user_id)
        for user_id
        in req.POST.getlist("user_ids")
        if str(user_id).isdigit()
    }

    if not requested_ids:
        messages.error(
            req,
            "Selecciona al menos un auditor.",
        )

        return redirect(
            "manage_audit",
            audit_id,
        )

    assigned_ids = (
        audit.assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    eligible_ids = {
        str(user_id)
        for user_id
        in User.objects
        .filter(
            id__in=requested_ids,
            administrador=req.user,
            is_deleted=False,
            is_active=True,
        )
        .exclude(
            id__in=assigned_ids,
        )
        .values_list(
            "id",
            flat=True,
        )
    }

    if eligible_ids != requested_ids:
        messages.error(
            req,
            (
                "Uno o varios usuarios seleccionados "
                "no pertenecen a tu equipo, están "
                "inactivos o ya están asignados."
            ),
        )

        return redirect(
            "manage_audit",
            audit_id,
        )

    try:
        multiple_assign_audit(
            sorted(eligible_ids),
            audit.id,
            req.user.id,
        )

        messages.success(
            req,
            (
                "Los auditores seleccionados fueron "
                "asignados correctamente."
            ),
        )

    except Exception as error:
        error_message = str(error)

        if isinstance(
            error,
            AUDIT_ERROR_INSTANCES,
        ):
            messages.error(
                req,
                error_message,
            )
        else:
            messages.error(
                req,
                (
                    "No fue posible asignar los "
                    "auditores seleccionados."
                ),
            )

    return redirect(
        "manage_audit",
        audit_id,
    )

@login_required
@audit_manager_required
def unassign_audit(req: HttpRequest, audit_id: int, user_id: int):
    try:
        unassign_audit_func(audit_id, user_id, req.user.id)
        messages.success(req, "La Auditoría fue removida del usuario exitosamente.")
        return redirect("manage_audit", audit_id)
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("manage_audit", audit_id)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, AUDIT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("manage_audit", audit_id)
        else:
            messages.error(req, error_message)
            return redirect("manage_audit", audit_id)


@login_required
@require_POST
def update_audit_row(
    req,
    audit_id,
):
    """
    Guarda Avance, Riesgo y Estado desde la tabla
    principal del módulo Auditorías.

    Para modificar una auditoría se requiere:
    - Auditorías → Editar.
    - Pertenecer al mismo equipo.
    - Estar asignado a la auditoría, salvo el Jefe.
    """

    try:
        audit = get_audit_for_user_or_404(
            req.user,
            audit_id,
            action="edit",
            module="audits",
        )

    except Http404:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "La auditoría no existe "
                    "o no tienes acceso."
                ),
            },
            status=404,
        )

    try:
        progress = int(
            req.POST.get(
                "progress",
                "",
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "El avance ingresado "
                    "no es válido."
                ),
            },
            status=400,
        )

    risk_level = req.POST.get(
        "risk_level",
        "",
    )

    workflow_status = req.POST.get(
        "workflow_status",
        "",
    )

    valid_progress_values = {
        0,
        10,
        25,
        50,
        65,
        75,
        88,
        100,
    }

    valid_risks = {
        value
        for value, _label
        in Audit.RISK_CHOICES
    }

    valid_statuses = {
        value
        for value, _label
        in Audit.STATUS_CHOICES
    }

    if progress not in valid_progress_values:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "El avance seleccionado "
                    "no es válido."
                ),
            },
            status=400,
        )

    if risk_level not in valid_risks:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "El nivel de riesgo "
                    "seleccionado no es válido."
                ),
            },
            status=400,
        )

    if workflow_status not in valid_statuses:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "El estado seleccionado "
                    "no es válido."
                ),
            },
            status=400,
        )

    manual_findings = req.POST.get("manual_findings_count")
    if manual_findings is not None:
        try:
            numeric = int(manual_findings)
            if numeric < 0 or numeric > 100000: raise ValueError("Límite excedido")
        except (ValueError, TypeError):
            return JsonResponse({"success": False, "message": "Número de hallazgos inválido"}, status=400)
        audit.manual_findings_count = numeric

    audit.progress = progress
    audit.risk_level = risk_level
    audit.workflow_status = workflow_status
    audit.updated_at = timezone.now()

    audit.save(
        update_fields=[
            "progress",
            "risk_level",
            "workflow_status",
            *(["manual_findings_count"] if manual_findings is not None else []),
            "updated_at",
        ]
    )

    return JsonResponse(
        {
            "success": True,
            "message": "Cambios guardados.",
            "manual_findings_count": audit.manual_findings_count,
            "progress": audit.progress,
            "risk_level": audit.risk_level,
            "workflow_status": (
                audit.workflow_status
            ),
        },
        status=200,
    )


@login_required
def assigned_audits_page(req: HttpRequest):
    """
    Pantalla principal del módulo Auditorías.

    El Jefe de Auditoría mantiene acceso administrativo.
    Los integrantes reciben los permisos configurados
    en la Matriz de Permisos de su equipo.
    """

    role = getattr(
        req.user,
        "role",
        None,
    )

    role_name = (
        role.name
        if role
        else None
    )

    is_audit_manager = (
        role_name == "audit_manager"
    )

    is_operational_user = (
        role_name in {
            "auditor",
            "supervisor",
            "readonly",
        }
    )

    # El jefe conserva control total.
    # Los integrantes consultan la matriz de su equipo.
    can_view_audits = (
        is_audit_manager
        or has_module_permission(
            req.user,
            "audits",
            "view",
        )
    )

    can_create_audit = (
        is_audit_manager
        or has_module_permission(
            req.user,
            "audits",
            "create",
        )
    )

    can_edit_audits = (
        is_audit_manager
        or has_module_permission(
            req.user,
            "audits",
            "edit",
        )
    )

    can_delete_audits = (
        is_audit_manager
        or has_module_permission(
            req.user,
            "audits",
            "delete",
        )
    )

    if not can_view_audits:
        return HttpResponseForbidden(
            (
                "No tienes permiso para consultar "
                "el módulo de Auditorías."
            )
        )

    if is_audit_manager:
        audits_queryset = (
            Audit.objects
            .filter(
                audit_manager=req.user,
            )
        )

    elif is_operational_user:
        audits_queryset = (
            Audit.objects
            .filter(
                assigned_users=req.user,
                audit_manager_id=(
                    req.user.administrador_id
                ),
            )
        )

    else:
        audits_queryset = (
            Audit.objects.none()
        )
        
    audits_queryset = (
        audits_queryset
        .annotate(
            active_findings_count=Count(
                "findings",
                filter=Q(
                    findings__is_active=True
                ),
                distinct=True,
            )
        )
    )
        
        

    audits_queryset = (
        audits_queryset
        .select_related(
            "audit_manager",
        )
        .prefetch_related(
            "assigned_users",
        )
        .distinct()
        .order_by(
            "-created_at",
            "-id",
        )
    )

    show_team_assignment = (
        is_audit_manager
        and req.user.modalidad == "G"
    )

    if show_team_assignment:
        assignable_auditors = (
            User.objects
            .filter(
                administrador=req.user,
                is_deleted=False,
                is_active=True,
            )
            .exclude(
                id=req.user.id,
            )
            .select_related(
                "role",
            )
            .order_by(
                "first_name",
                "last_name",
                "username",
            )
        )

    else:
        assignable_auditors = (
            User.objects.none()
        )

    has_assignable_auditors = (
        assignable_auditors.exists()
    )

    team_owner = get_team_owner(
    req.user
    )

    manager_user = (
        team_owner
        if team_owner
        else req.user
    )

    manager_name = (
        manager_user.get_full_name()
        or manager_user.username
    )

    now = timezone.now()

    audit_rows = [
        _build_audit_row(
            audit,
            now,
        )
        for audit in audits_queryset
    ]

    total_audits = len(
        audit_rows
    )

    active_audits = sum(
        1
        for row in audit_rows
        if row["status_slug"] != "completed"
    )

    completed_audits = sum(
        1
        for row in audit_rows
        if row["status_slug"] == "completed"
    )
    
    total_findings = sum(
            int(
                row.get(
                    "findings",
                    0,
                )
                or 0
            )
            for row in audit_rows
        )

    context = {
        "audit_rows": audit_rows,

        "total_audits": total_audits,
        "active_audits": active_audits,
        "completed_audits": completed_audits,
        "total_findings": total_findings,

        # Permisos efectivos
        "can_view_audits": can_view_audits,
        "can_create_audit": can_create_audit,
        "can_edit_audits": can_edit_audits,
        "can_delete_audits": can_delete_audits,

        # Solo el jefe puede abrir la administración completa
        "can_manage_audits": is_audit_manager,
        "can_configure_permissions": is_audit_manager,

        "assignable_auditors": (
            assignable_auditors
        ),
        "has_assignable_auditors": (
            has_assignable_auditors
        ),
        "show_team_assignment": (
            show_team_assignment
        ),
        "manager_name": manager_name,
        "can_create_revisoria": client_can_create_audit_type(manager_user, "R"),
        "can_create_interna": client_can_create_audit_type(manager_user, "I"),
    }

    return render(
        req,
        "audits/assigned-audits.html",
        context,
    )

@audit_manager_required
@login_required
def manage_audit_page(req, audit_id):
    data = {}
    audit_to_manage = get_object_or_404(Audit, pk=audit_id, audit_manager=req.user)

    if req.user != audit_to_manage.audit_manager:
        return redirect("assigned_audits")

    data["audit_to_manage"] = audit_to_manage
    
    audit_row = _build_audit_row(
        audit_to_manage,
        timezone.now(),
    )

    data["audit_row"] = audit_row

    data["active_type_codes"] = (
        audit_to_manage.get_active_type_codes()
    )

    data["risk_choices"] = (
        Audit.RISK_CHOICES
    )

    data["status_choices"] = (
        Audit.STATUS_CHOICES
    )

    data["progress_options"] = [
        0,
        10,
        25,
        50,
        65,
        75,
        88,
        100,
    ]
    
    # Pasar la modalidad del usuario a la plantilla
    data["user_modalidad"] = req.user.modalidad

    assigned_users = (
    audit_to_manage.assigned_users
    .select_related("role")
    .order_by(
        "first_name",
        "last_name",
        "username",
    )
)

    assigned_user_ids = (
        assigned_users.values_list(
            "id",
            flat=True,
        )
    )

    available_users = (
        User.objects
        .filter(
            administrador=req.user,
            is_deleted=False,
            is_active=True,
        )
        .exclude(
            id__in=assigned_user_ids,
        )
        .select_related("role")
        .order_by(
            "first_name",
            "last_name",
            "username",
        )
    )

    data["assigned_users"] = assigned_users
    data["available_users"] = available_users

    data["assigned_users_count"] = (
        assigned_users.count()
    )

    data["available_users_count"] = (
        available_users.count()
    )

    return render(req, "audits/manage-audit.html", data)


@login_required
@audit_manager_required
def unassign_audit_page(req, audit_id, user_id):
    return


@login_required
@audit_manager_required
def delete_audit_page(req, audit_id):
    return
