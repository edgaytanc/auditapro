"""Dashboard manual de Auditoría Interna.

NO lee ni escribe Audit, InternalAuditPlan, cronogramas o hallazgos.
El contenido es exclusivamente una vista manual almacenada en el navegador.
Las vistas de detalle productivas permanecen en internal_audit.views.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from users.permissions import module_permission_required


@login_required
@module_permission_required("audits", "view")
def dashboard_interna_manual(request):
    return render(request, "internal_audit/list.html", {
        "manual_dashboard_user_id": request.user.pk,
    })
