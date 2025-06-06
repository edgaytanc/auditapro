from django.urls import path
from . import views

urlpatterns = [
    path("", views.archivo, name="archivo_permanente"),
    path("descargar/<str:nombre_archivo>/", views.descargar_archivo, name="descargar_archivo"),
]
