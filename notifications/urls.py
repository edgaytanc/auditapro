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
]
