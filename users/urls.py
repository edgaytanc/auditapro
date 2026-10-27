from django.contrib.auth import (
    views as auth_views,
)
from django.urls import include, path

from . import views
from .financial_identity import save_financial_company


urlpatterns = [
    path(
        "",
        views.index_page,
        name="home",
    ),
    path(
        "user/",
        views.user_page,
        name="user",
    ),
    path(
        "edit_field/<str:field>",
        views.edit_user,
        name="edit_field",
    ),
    path(
        "login/",
        views.login,
        name="login",
    ),
    path(
        "signup/",
        views.signup,
        name="signup",
    ),
    path(
        "demo_signup/",
        views.demo_signup,
        name="demo_signup",
    ),
    path(
        "logout/",
        views.logout,
        name="logout",
    ),
    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),

    # Nombre manual de la entidad, compartido por los 3 módulos financieros.
    path("dashboard/financiera/nombre-empresa/", save_financial_company, name="financial_company_save"),

    # Exportación XLSX verdadera con datos y mapa de calor.
    path("dashboard/financiera/matriz-riesgos/exportar/", views.exportar_matriz_riesgos, name="exportar_matriz_riesgos"),

    # Dashboard de Auditoría Financiera
    path(
        "dashboard/financiera/",
        views.dashboard_financiera,
        name="dashboard_financiera",
    ),
    path(
        "dashboard/financiera/matriz-riesgos/",
        views.matriz_riesgos_financiera,
        name="matriz_riesgos_financiera",
    ),
    path(
        "dashboard/financiera/hallazgos/",
        views.hallazgos_financiera,
        name="hallazgos_financiera",
    ),
    path(
        "dashboard/financiera/informe-final/",
        views.informe_final_financiera,
        name="informe_final_financiera",
    ),

    # Módulo independiente de Auditoría Interna
    path(
        "dashboard/interna/",
        include(
            "internal_audit.urls"
        ),
    ),

    path(
        "delete_account/",
        views.delete_account,
        name="delete_account",
    ),
    path(
        "socios/ingreso/",
        views.login_audit_manager,
        name="login_audit_manager",
    ),
    path(
        "socios/crear-usuario/",
        views.partner_create_user,
        name="partner_create_user",
    ),
    path(
        "activate/<uidb64>/<token>/",
        views.activate_account,
        name="activate_account",
    ),
    path(
        "autoregistro/",
        views.socio_autoregistro,
        name="socio_autoregistro",
    ),
    path(
        (
            "autoregistro/registro/"
            "<str:token>/"
        ),
        views.autoregistro_registro,
        name="autoregistro_registro",
    ),

    # Restablecimiento de contraseña
    path(
        "reset_password/",
        auth_views.PasswordResetView.as_view(
            template_name=(
                "users/password_reset.html"
            )
        ),
        name="reset_password",
    ),
    path(
        "reset_password_sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name=(
                "users/password_reset_sent.html"
            )
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name=(
                "users/password_reset_form.html"
            )
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset_password_complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name=(
                "users/password_reset_done.html"
            )
        ),
        name="password_reset_complete",
    ),
]