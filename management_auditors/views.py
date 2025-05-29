from django.shortcuts import render, redirect
from audits.decorators import audit_manager_required
from django.contrib.auth.decorators import login_required
from audits.models import Audit
from django.contrib.auth import get_user_model
from audits.services import assign_audit_to_user
from django.contrib import messages
from .const import MANAGEMENT_AUDITORS_ERROR_INSTANCES
from .services import get_user_to_manage
from django.http import Http404

User = get_user_model()


@login_required
@audit_manager_required
def manage_auditors_page(req):
    users_to_manage = User.objects.exclude(username=req.user.username)
    return render(
        req,
        "management_auditors/manage-auditors.html",
        {"users_to_manage": users_to_manage},
    )


@login_required
@audit_manager_required
def manage_auditor_page(req, user_id):
    data = {}
    audits = Audit.objects.filter(audit_manager=req.user)
    data["audits"] = audits
    try:
        user_to_manage = get_user_to_manage(req.user.id, user_id)

        data["user_to_manage"] = user_to_manage

        return render(req, "management_auditors/manage-auditor.html", data)
    except Exception as e:
        raise Http404("User not found")


@login_required
@audit_manager_required
def assign_audit(req, user_id):
    audits_ids: list[str] = req.POST.getlist("audits_ids")
    try:
        assign_audit_to_user(user_id, audits_ids, req.user.id)
        messages.success(
            req,
            f"Se le han asignado las auditorías correctamente al usuario seleccionado.",
        )
        return redirect("manage_auditor", user_id)
    except ValueError as e:
        messages.error(
            req,
            "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.",
        )

        return redirect("manage_auditor", user_id)

    except Exception as e:
        error_message = str(e)
        if isinstance(e, MANAGEMENT_AUDITORS_ERROR_INSTANCES):
            messages.error(req, error_message)

            return redirect("manage_auditor", user_id)

        else:
            messages.error(
                req, "Ocurrió un error inesperado, por favor inténtelo de nuevo."
            )
            return redirect("manage_auditor", user_id)
