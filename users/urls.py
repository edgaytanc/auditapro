from django.urls import path
from users import views

urlpatterns = [
    path("", views.index_page, name="home"),
    path("user/", views.user_page, name="user"),
    path("edit_field/<str:field>", views.edit_user, name="edit_field"),
    path("login/", views.login, name="login"),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("delete_account/", views.delete_account, name="delete_account"),
]
