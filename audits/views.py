from django.shortcuts import render, get_object_or_404, redirect

from audits.utils import get_assigned_audits
from .decorators import audit_manager_required
from .models import Audit
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from audits.services import (
    unassign_audit as unassign_audit_func,
    delete_audit as delete_audit_func,
    create_audit as create_audit_func,
    assign_audit as assign_audit_func,
    multiple_assign_audit,
    update_audit,
)
from django.contrib import messages
from .consts import AUDIT_ERROR_INSTANCES

User = get_user_model()


@login_required
def assigned_audits(req):
    if req.method == "GET":
        return assigned_audits_page(req)


@login_required
@audit_manager_required
def create_audit_view(req: HttpRequest):
    if req.method == "GET":
        return create_audit_page(req)
    elif req.method == "POST":
        return create_audit(req)


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
@audit_manager_required
def delete_audit_view(req, audit_id):
    if req.method == "POST":
        return delete_audit(req, audit_id)
    elif req.method == "GET":
        return delete_audit_page(req, audit_id)


@login_required
@audit_manager_required
def create_audit(req):
    company = req.POST.get("audit_company")
    description = req.POST.get("audit_description")
    title = req.POST.get("audit_title")
    audit_assigned_users_ids = req.POST.getlist("audit_assigned_users_ids")
    try:
        create_audit_func(
            req.user, title, description, company, audit_assigned_users_ids
        )
        messages.success(req, "Auditoría creada exitosamente.")
        return redirect("create_audit")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("create_audit")

    except Exception as e:
        error_message = str(e)
        if isinstance(e, AUDIT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("create_audit")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("create_audit")


@login_required
@audit_manager_required
def delete_audit(req, audit_id):
    try:
        delete_audit_func(audit_id, req.user.id)
        messages.success(req, "La Auditoría fue borrada exitosamente.")
        return redirect("assigned_audits")
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )
        return redirect("assigned_audits")
    except Exception as e:
        error_message = str(e)
        if isinstance(e, AUDIT_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("assigned_audits")
        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("assigned_audits")


@login_required
@audit_manager_required
def create_audit_page(req):
    data = {}
    users_to_assign_audits = User.objects.exclude(username=req.user.username)

    select_options = [
        {
            "option_value": user.id,
            "text_to_show1": user.get_full_name(),
            "text_to_show2": user.role,
        }
        for user in users_to_assign_audits
    ]

    data["users_to_asiggn_audits"] = users_to_assign_audits
    data["select_options"] = select_options

    return render(
        req,
        "audits/create-audit.html",
        data,
    )


@audit_manager_required
@login_required
def manage_audit(req, audit_id):
    audit_title = req.POST.get("audit_title")
    audit_description = req.POST.get("audit_description")
    audit_company = req.POST.get("audit_company")
    try:
        update_audit(
            audit_id, audit_title, audit_description, audit_company, req.user.id
        )
        messages.success(req, "Auditoria modificada exitosamente.")
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
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("manage_audit", audit_id)


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
    user_ids = req.POST.getlist("user_ids")
    try:
        multiple_assign_audit(user_ids, audit_id, req.user.id)
        messages.success(
            req, "La Auditoría fue asignada a los usuarios seleccionados con éxito."
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
def assigned_audits_page(req: HttpRequest):
    data = {}
    user_role = req.user.role.name

    if user_role == "audit_manager":
        data["audits_to_manage"] = get_assigned_audits(user_role=user_role, req=req)

    elif user_role == "supervisor" or user_role == "auditor":
        data["assigned_audits"] = get_assigned_audits(user_role=user_role, req=req)
    return render(req, "audits/assigned-audits.html", data)


@audit_manager_required
@login_required
def manage_audit_page(req, audit_id):
    data = {}
    audit_to_manage = get_object_or_404(Audit, pk=audit_id, audit_manager=req.user)

    if req.user != audit_to_manage.audit_manager:
        return redirect("assigned_audits")

    data["audit_to_manage"] = audit_to_manage

    users_that_can_be_assigned = [
        {
            "option_value": user.id,
            "text_to_show1": user.get_full_name(),
            "text_to_show2": user.role,
        }
        for user in User.objects.exclude(username=req.user.username)
    ]
    data["users_that_can_be_assigned"] = users_that_can_be_assigned

    assigned_users = audit_to_manage.assigned_users.all()
    data["assigned_users"] = assigned_users

    return render(req, "audits/manage-audit.html", data)


@login_required
@audit_manager_required
def unassign_audit_page(req, audit_id, user_id):
    return


@login_required
@audit_manager_required
def delete_audit_page(req, audit_id):
    return
