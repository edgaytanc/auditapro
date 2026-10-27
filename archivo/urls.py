from django.urls import path
from . import views, manual_views

urlpatterns = [
    # Solo la pantalla principal cambia al modo manual.
    path("", manual_views.archivo_manual, name="archivo_permanente"),
    # Mantener rutas existentes para compatibilidad con enlaces anteriores.
    # NO se utilizan desde la nueva interfaz manual.
    path("exportar/<str:formato>/<str:seccion>/", views.exportar_archivo_permanente, name="exportar_archivo_permanente"),
    path("descargar/<str:nombre_archivo>/", views.descargar_archivo, name="descargar_archivo"),
]
