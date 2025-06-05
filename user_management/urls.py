from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_list, name='user_list'),
    path('create/', views.create_user, name='create_user'),
    path('dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('<int:user_id>/', views.user_details, name='user_details'),
    path('<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('<int:user_id>/deactivate/', views.deactivate_user, name='deactivate_user'),
    path('<int:user_id>/reactivate/', views.reactivate_user, name='reactivate_user'),
]
