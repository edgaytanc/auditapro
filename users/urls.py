from django.urls import path
from users import views
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.index_page, name="home"),
    path("user/", views.user_page, name="user"),
    path("edit_field/<str:field>", views.edit_user, name="edit_field"),
    path("login/", views.login, name="login"),
    path("signup/", views.signup, name="signup"),
    path("demo_signup/", views.demo_signup, name="demo_signup"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("delete_account/", views.delete_account, name="delete_account"),
    path('socios/ingreso/', views.login_audit_manager, name='login_audit_manager'),
    path('socios/crear-usuario/', views.partner_create_user, name='partner_create_user'),
    path('activate/<uidb64>/<token>/', views.activate_account, name='activate_account'),
    path('autoregistro/', views.socio_autoregistro, name='socio_autoregistro'),
    path('autoregistro/registro/<str:token>/', views.autoregistro_registro, name='autoregistro_registro'),




    # URLs para restablecer la contraseña
    path('reset_password/', 
         auth_views.PasswordResetView.as_view(template_name="users/password_reset.html"), 
         name="reset_password"),

    path('reset_password_sent/', 
         auth_views.PasswordResetDoneView.as_view(template_name="users/password_reset_sent.html"), 
         name="password_reset_done"),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name="users/password_reset_form.html"), 
         name="password_reset_confirm"),
    
    path('reset_password_complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name="users/password_reset_done.html"), 
         name="password_reset_complete"),
]
