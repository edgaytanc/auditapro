from django.urls import path
from . import views

from .export_excel import exportar_auditorias_excel

urlpatterns = [
    path("exportar-excel/", exportar_auditorias_excel, name="exportar_auditorias_excel"),
    path("", views.assigned_audits, name="assigned_audits"),
    path(
    "matriz-permisos/",
    views.role_permissions_matrix,
    name="role_permissions_matrix",
    ),
    path(
    "<int:audit_id>/actualizar-fila/",
    views.update_audit_row,
    name="update_audit_row",
    ),
    path("crear/", views.create_audit_view, name="create_audit"),
    path(
        "gestionar_auditoria/<str:audit_id>/",
        views.manage_audit_view,
        name="manage_audit",
    ),
    path("gestionar_auditoria/", views.manage_audit_redirect),
    path(
        "<str:audit_id>/unassign/<str:user_id>/",
        views.unassign_audit_view,
        name="unassign_audit",
    ),
    path(
        "<str:audit_id>/assign/<str:user_id>", views.assign_audit, name="assign_audit"
    ),
    path(
        "<str:audit_id>/manage_audit_assign_audit/",
        views.manage_audit_assign_audit,
        name="manage_audit_assign_audit",
    ),
    path("<str:audit_id>/delete_audit/", views.delete_audit_view, name="delete_audit"),
]
