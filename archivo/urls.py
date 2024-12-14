from django.urls import path
from . import views

urlpatterns = [
    path("", views.archivo, name="archivo_permanente"),
]
