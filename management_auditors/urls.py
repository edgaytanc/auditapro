from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.manage_auditors_page,
        name="manage_auditors",
    ),
    path(
        "add/",
        views.add_auditor,
        name="add_auditor",
    ),
    path(
        "<int:user_id>/eliminar-permanentemente/",
        views.hard_delete_auditor,
        name="hard_delete_auditor",
    ),
    path(
        "<int:user_id>/cambiar-rol/",
        views.update_auditor_role,
        name="update_auditor_role",
    ),
    path(
        "<int:user_id>/retirar/",
        views.delete_auditor,
        name="delete_auditor",
    ),
    path(
        "<int:user_id>/",
        views.manage_auditor_page,
        name="manage_auditor",
    ),
    path(
        "asignar_auditoria/<int:user_id>/",
        views.assign_audit,
        name="assign_audit",
    ),
]