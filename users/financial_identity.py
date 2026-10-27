"""Nombre editable compartido por Matriz de Riesgos, Hallazgos e Informe.
Se separa de Audit.identidad para no afectar documentos base ni datos del cliente.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import FinancialDashboardIdentity


def identity_scope(request):
    selected = request.session.get("selected_audit")
    if isinstance(selected, dict):
        audit_id = selected.get("id")
        try:
            if int(audit_id) > 0:
                return f"audit:{int(audit_id)}"
        except (TypeError, ValueError):
            pass
    return "general"


def financial_company(request):
    scope = identity_scope(request)
    saved = FinancialDashboardIdentity.objects.filter(user=request.user, scope_key=scope).first()
    if saved:
        return saved.company_name
    selected = request.session.get("selected_audit")
    if scope != "general" and isinstance(selected, dict):
        return str(selected.get("identidad") or "")[:255]
    return ""


@login_required
@require_POST
def save_financial_company(request):
    name = " ".join(request.POST.get("company_name", "").split())
    if not 1 <= len(name) <= 255:
        return JsonResponse({"error": "El nombre debe tener entre 1 y 255 caracteres."}, status=400)
    FinancialDashboardIdentity.objects.update_or_create(
        user=request.user,
        scope_key=identity_scope(request),
        defaults={"company_name": name},
    )
    return JsonResponse({"ok": True, "company_name": name})
