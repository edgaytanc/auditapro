"""
Vistas para gestión de auditorías.

Contiene listados antiguos y la pantalla de detalle.
Todos los accesos se validan mediante la matriz
y el equipo propietario.
"""

import json
import os
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from audits.access import user_can_access_audit_type, allowed_audit_type_codes

from audits.access import (
    get_audit_for_user_or_404,
)
from users.permissions import (
    module_permission_required,
)

from .config import (
    Audit,
    HttpResponse,
    login_required,
    mark_safe,
    redirect,
    render,
    settings,
)
from .utils import (
    crear_mensaje_error,
    generar_html_estructura,
)
from auditoria.services.agrupacion_plantillas_ui import filtrar_estructura_visible_productivo


def _get_audits_for_user(
    user,
    audit_type,
):
    """
    Retorna auditorías del tipo indicado
    pertenecientes al equipo del usuario.
    """

    # Priorizar nuevos flags y usar tipoAuditoria solo para proyectos antiguos
    # cuyos tres flags nunca fueron definidos.
    if not user_can_access_audit_type(user, audit_type):
        return Audit.objects.none()

    field = {"F": "activa_financiera", "R": "activa_revisoria", "I": "activa_interna"}[audit_type]
    queryset = Audit.objects.filter(
        Q(**{field: True})
        | Q(
            activa_financiera=False,
            activa_revisoria=False,
            activa_interna=False,
            tipoAuditoria=audit_type,
        )
    )

    if user.is_superuser or user.is_staff:
        return queryset.distinct()

    role = getattr(
        user,
        "role",
        None,
    )

    role_name = getattr(
        role,
        "name",
        None,
    )

    if role_name == "audit_manager":
        return (
            queryset
            .filter(
                audit_manager=user,
            )
            .distinct()
        )

    owner_id = getattr(
        user,
        "administrador_id",
        None,
    )

    if not owner_id:
        return Audit.objects.none()

    return (
        queryset
        .filter(
            assigned_users=user,
            audit_manager_id=owner_id,
        )
        .distinct()
    )


def _validate_selected_audit(request, audit_type):
    audit_id = request.POST.get("audit_id")
    audit = get_audit_for_user_or_404(
        request.user, audit_id, action="view", module="audits",
    )
    if audit_type not in audit.get_active_type_codes() or not user_can_access_audit_type(request.user, audit_type):
        raise Http404("Esta auditoría no tiene habilitado ese módulo para tu usuario.")
    return audit_id


@login_required
@module_permission_required(
    "audits",
    "view",
)
def auditorias_view(request):
    return render(
        request,
        "auditoria/auditorias.html",
        {},
    )


@login_required
@module_permission_required(
    "audits",
    "view",
)
def auditoria_financiera_view(request):
    auditorias_financieras = (
        _get_audits_for_user(
            request.user,
            "F",
        )
    )

    if request.method == "POST":
        audit_id = _validate_selected_audit(request, "F")
        return redirect(f"{reverse('auditoria_detalle', args=[audit_id])}?tipo=F")

    return render(
        request,
        (
            "auditoria/auditoria-financiera/"
            "auditoria_financiera.html"
        ),
        {
            "auditorias": (
                auditorias_financieras
            ),
        },
    )


@login_required
@module_permission_required(
    "audits",
    "view",
)
def auditoria_interna_view(request):
    auditorias_internas = (
        _get_audits_for_user(
            request.user,
            "I",
        )
    )

    if request.method == "POST":
        audit_id = _validate_selected_audit(request, "I")
        return redirect(f"{reverse('auditoria_detalle', args=[audit_id])}?tipo=I")

    return render(
        request,
        (
            "auditoria/auditoria-interna/"
            "auditoria_interna.html"
        ),
        {
            "auditorias": (
                auditorias_internas
            ),
        },
    )


@login_required
@module_permission_required(
    "audits",
    "view",
)
def auditoria_revisoria_view(request):
    auditorias_revisorias = (
        _get_audits_for_user(
            request.user,
            "R",
        )
    )

    if request.method == "POST":
        audit_id = _validate_selected_audit(request, "R")
        return redirect(f"{reverse('auditoria_detalle', args=[audit_id])}?tipo=R")

    return render(
        request,
        (
            "auditoria/revisoria-fiscal/"
            "revisoria.html"
        ),
        {
            "auditorias": (
                auditorias_revisorias
            ),
        },
    )


@login_required
@module_permission_required(
    "audits",
    "view",
)
def auditoria_detalle_view(
    request,
    audit_id,
):
    """
    Muestra el expediente de una auditoría.

    Exige:
    - Permiso Auditorías → Ver.
    - Auditoría del mismo equipo.
    - Estar asignado, salvo que sea el Jefe.
    """

    audit = get_audit_for_user_or_404(
        request.user,
        audit_id,
        action="view",
        module="audits",
    )

    available_types = allowed_audit_type_codes(request.user, audit)
    preferred_type = request.GET.get("tipo") or audit.tipoAuditoria
    if request.GET.get("tipo") and preferred_type not in available_types:
        raise Http404("Este módulo no está habilitado para tu usuario o proyecto.")
    current_type = preferred_type if preferred_type in available_types else (available_types[0] if available_types else None)
    if current_type is None:
        raise Http404("No tienes acceso a los módulos de esta auditoría.")

    if current_type == "I":
        structure_filename = (
            "folder_structure_interna.json"
        )

    elif current_type == "R":
        structure_filename = (
            "folder_structure_revisoria.json"
        )

    else:
        structure_filename = (
            "folder_structure_financiera.json"
        )

    json_path = os.path.join(
        settings.BASE_DIR,
        "auditoria",
        "config",
        structure_filename,
    )

    try:
        with open(
            json_path,
            "r",
            encoding="utf-8",
        ) as structure_file:
            estructura_carpetas = json.load(
                structure_file
            )

    except Exception:
        estructura_carpetas = {}

    user_verified = (
        request.user.username
        == "administrador"
        or (
            hasattr(
                request.user,
                "plan",
            )
            and request.user.plan
            in {
                "M",
                "A",
            }
        )
    )

    # El árbol mostrado respeta los 430 documentos referenciados por el
    # catálogo productivo. El catálogo operativo y las descargas no cambian.
    estructura_visible = filtrar_estructura_visible_productivo(
        estructura_carpetas, current_type,
    )

    estructura_html = (
        generar_html_estructura(
            estructura_visible,
            audit.id,
            user_verified=user_verified,
            tipo_auditoria=current_type,
        )
    )

    return render(
        request,
        (
            "auditoria/auditoria-detalle/"
            "auditoria_detalle.html"
        ),
        {
            "audit": audit,
            "audit_type": current_type,
            "estructura_html": mark_safe(
                estructura_html
            ),
            "user_verified": user_verified,
        },
    )