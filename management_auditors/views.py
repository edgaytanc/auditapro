from django.shortcuts import render, redirect
from audits.decorators import audit_manager_required, group_admin_required
from django.contrib.auth.decorators import login_required
from audits.models import Audit
from django.contrib.auth import get_user_model
from audits.services import assign_audit_to_user
from django.contrib import messages
from .const import MANAGEMENT_AUDITORS_ERROR_INSTANCES
from .services import get_user_to_manage
from django.http import Http404
from .forms import AuditorCreationForm

User = get_user_model()


def _get_max_users(user):
    """
    Cupo máximo dinámico para auditores.
    - Solo aplica si el admin está en modalidad grupal (G).
    - Mínimo 3.
    """
    if getattr(user, "modalidad", None) != "G":
        return 0

    max_users = getattr(user, "auditor_slots", None) or 3
    if max_users < 3:
        max_users = 3
    return max_users


# ✅ Alias para compatibilidad: urls.py puede llamar manage_auditors_page
@login_required
@group_admin_required
def manage_auditors_page(req):
    return manage_auditors(req)


@login_required
@group_admin_required
def manage_auditors(req):
    """
    Página para gestionar auditores del jefe de auditoría (modalidad grupal).
    El cupo máximo viene de req.user.auditor_slots (mínimo 3).
    """
    users_qs = User.objects.filter(
        administrador=req.user,
        is_deleted=False
    ).order_by("id")

    user_count = users_qs.count()
    max_users = _get_max_users(req.user)
    can_add_more_users = user_count < max_users

    return render(req, "management_auditors/manage-auditors.html", {
        # ✅ Nombres que tu template puede estar esperando
        "users_to_manage": users_qs,
        "user_count": user_count,

        # ✅ Extras útiles para UI (cupo, botón añadir)
        "max_users": max_users,
        "can_add_more_users": can_add_more_users,

        # ✅ Compatibilidad por si otro template usa estos nombres
        "users": users_qs,
        "current_users": user_count,
        "max_auditors": max_users,
    })


@login_required
@group_admin_required
def add_auditor(req):
    """
    Crear auditor respetando cupo dinámico (auditor_slots, mínimo 3).
    """
    max_users = _get_max_users(req.user)

    current_auditors_count = User.objects.filter(
        administrador=req.user,
        is_deleted=False
    ).count()

    if current_auditors_count >= max_users:
        messages.error(
            req,
            f"No puedes añadir más usuarios. Has alcanzado el límite de {max_users} usuarios."
        )
        return redirect("manage_auditors")

    if req.method == "POST":
        form = AuditorCreationForm(req.POST)
        if form.is_valid():
            form.save(admin_user=req.user)
            messages.success(req, "Usuario auditor creado exitosamente.")
            return redirect("manage_auditors")
    else:
        form = AuditorCreationForm()

    return render(req, "management_auditors/add_auditor.html", {"form": form})


@login_required
@audit_manager_required
def manage_auditor_page(req, user_id):
    try:
        user_to_manage = get_user_to_manage(req.user.id, user_id)

        # Auditorías asignadas a este auditor
        audits = Audit.objects.filter(assigned_users=user_to_manage)

        return render(req, "management_auditors/manage-auditor.html", {
            "audits": audits,
            "user_to_manage": user_to_manage
        })
    except Exception:
        raise Http404("User not found")


@login_required
@audit_manager_required
def assign_audit(req, user_id):
    audits_ids = req.POST.getlist("audits_ids")
    try:
        assign_audit_to_user(user_id, audits_ids, req.user.id)
        messages.success(req, "Se le han asignado las auditorías correctamente al usuario seleccionado.")
        return redirect("manage_auditor", user_id)
    except ValueError:
        messages.error(req, "Alguno de los valores ingresados es inválido, por favor, ingrese los valores correctamente.")
        return redirect("manage_auditor", user_id)
    except Exception as e:
        error_message = str(e)
        if isinstance(e, MANAGEMENT_AUDITORS_ERROR_INSTANCES):
            messages.error(req, error_message)
            return redirect("manage_auditor", user_id)

        messages.error(req, "Ocurrió un error inesperado, por favor inténtelo de nuevo.")
        return redirect("manage_auditor", user_id)
