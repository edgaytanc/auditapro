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


@login_required
@group_admin_required
def manage_auditors_page(req):
    # Obtener solo los auditores asociados a este administrador
    users_to_manage = User.objects.filter(administrador=req.user)
    
    # Verificar si el administrador ya alcanzó el límite de 3 usuarios
    can_add_more_users = users_to_manage.count() < 3
    
    return render(
        req,
        "management_auditors/manage-auditors.html",
        {
            "users_to_manage": users_to_manage,
            "can_add_more_users": can_add_more_users,
            "user_count": users_to_manage.count(),
            "max_users": 3
        },
    )


@login_required
@group_admin_required
def add_auditor(req):
    # Verificar si el administrador ya alcanzó el límite de 3 usuarios
    current_auditors_count = User.objects.filter(administrador=req.user).count()
    if current_auditors_count >= 3:
        messages.error(req, "No puedes añadir más usuarios. Has alcanzado el límite de 3 usuarios.")
        return redirect('manage_auditors')
    
    if req.method == 'POST':
        form = AuditorCreationForm(req.POST)
        if form.is_valid():
            # Guardar el usuario con el administrador actual
            form.save(admin_user=req.user)
            messages.success(req, "Usuario auditor creado exitosamente.")
            return redirect('manage_auditors')
    else:
        form = AuditorCreationForm()
    
    return render(req, 'management_auditors/add_auditor.html', {'form': form})


@login_required
@audit_manager_required
def manage_auditor_page(req, user_id):
    data = {}
    try:
        user_to_manage = get_user_to_manage(req.user.id, user_id)
        
        # Obtener solo las auditorías asignadas a este auditor específico
        audits = Audit.objects.filter(assigned_users=user_to_manage)
        
        data["audits"] = audits
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
