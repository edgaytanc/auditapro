from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.tools_page,
        name="tools",
    ),
    path(
        "descargar/<str:nombre_archivo>/",
        views.descargar_herramienta,
        name="descargar_herramienta",
    ),
    path(
        "resumen-tiempo/",
        views.audit_time_summary_index,
        name="audit_time_summary_index",
    ),
    path(
        "resumen-tiempo/resumen-auditoria/",
        views.audit_time_summary_table_page,
        name="audit_time_summary_table",
    ),
    path(
        "resumen-tiempo/resumen-auditoria/<int:id>/",
        views.audit_time_summary,
        name="audit_time_summary",
    ),
    path(
        "resumen-tiempo/resumen-auditoria/crear/",
        views.audit_time_summary_create,
        name="create_audit_time_summary",
    ),
    path(
        "resumen-tiempo/resumen-auditoria/delete/<int:id>/",
        views.delete_audit_time_summary,
        name="delete_audit_time_summary",
    ),
    path(
        "resumen-tiempo/horas-trabajadas/",
        views.summary_hours_worked_table_page,
        name="summary_worked_hours_table",
    ),
    path(
        "resumen-tiempo/horas-trabajadas/<int:id>/",
        views.summary_hours_worked,
        name="summary_hours_worked",
    ),
    path(
        "resumen-tiempo/horas-trabajadas/delete/<int:id>/",
        views.delete_summary_hours_worked,
        name="delete_summary_hours_worked",
    ),
    path(
        "resumen-tiempo/horas-trabajadas/crear/",
        views.summary_hours_worked_create,
        name="create_summary_hours_worked",
    ),
    path(
        "resumen-tiempo/papeles-trabajo/",
        views.status_of_work_papers_table_page,
        name="status_of_work_papers_table",
    ),
    path(
        "resumen-tiempo/papeles-trabajo/crear/",
        views.status_of_work_papers_create,
        name="create_status_of_work_papers",
    ),
    path(
        "resumen-tiempo/papeles-trabajo/<int:id>/",
        views.status_of_work_papers,
        name="status_of_work_papers",
    ),
    path(
        "resumen-tiempo/papeles-trabajo/delete/<int:id>/",
        views.delete_status_of_work_papers,
        name="delete_status_of_work_papers",
    ),
    path("marcas-de-auditoria/", views.audit_marks_page, name="audit_marks"),
    path(
        "marcas-de-auditoria/crear/", views.audit_mark_create, name="create_audit_mark"
    ),
    path("marcas-de-auditoria/<int:id>/", views.audit_mark, name="audit_mark"),
    path(
        "marcas-de-auditoria/delete/<int:id>/",
        views.delete_audit_mark,
        name="delete_audit_mark",
    ),
    path("tipos-de-monedas/", views.currency_types_page, name="currency_types"),
    path("tipos-de-monedas/<int:id>/", views.currency_type, name="currency_type"),
    path(
        "tipos-de-monedas/crear/",
        views.currency_type_create,
        name="create_currency_type",
    ),
    path(
        "tipos-de-monedas/delete/<int:id>/",
        views.delete_currency_type,
        name="delete_currency_type",
    ),
    path("actividades/", views.activities_page, name="activities_page"),
    path("actividades/crear/", views.activity_create, name="create_activity"),
    path("actividades/<int:id>/", views.activity, name="activity"),
    path("actividades/delete/<int:id>/", views.delete_activity, name="delete_activity"),
    path(
        "activity-total-days-per-month/<int:id>/",
        views.activity_total_days_per_month,
        name="activity_total_days_per_month",
    ),
]
