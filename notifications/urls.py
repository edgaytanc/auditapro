from django.urls import path
from notifications import views

urlpatterns = [
    path("", views.notifications, name="notifications"),
    path("crear/", views.create_notification_view, name="create_notification"),
    path(
        "mark_as_read/<int:notification_status_id>/",
        views.mark_notification_as_read,
        name="mark_notification_as_read",
    ),

    # 🔹 Vista de detalle
    path("<int:pk>/", views.notification_detail, name="notification_detail"),

    # 🔹 Revisión (usada por el fetch del modal)
    path("<int:pk>/review/", views.review_notification, name="notification_review"),
    
    path("eliminar/", views.delete_notifications, name="delete_notifications"),
    path("status/<int:ns_id>/delete/", views.delete_notification_status, name="notification_delete_one"),
    

]
