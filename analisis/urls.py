from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="analisis_home"),
    path("nuevo/", views.nuevo, name="analisis_nuevo"),
    path("<int:pk>/", views.detalle, name="analisis_detalle"),
    path("<int:pk>/estado/", views.estado, name="analisis_estado"),
    path("<int:pk>/parar/", views.parar, name="analisis_parar"),
    path("<int:pk>/pegar/", views.pegar, name="analisis_pegar"),
    path("<int:pk>/descargar/", views.descargar, name="analisis_descargar"),
    path("<int:pk>/descargar/<int:numero>/", views.descargar, name="analisis_descargar_version"),
    path("<int:pk>/resultados.csv", views.resultados_csv, name="analisis_csv"),
    path("<int:pk>/validar/", views.validar, name="analisis_validar"),
    path("<int:pk>/aprobar/", views.aprobar, name="analisis_aprobar"),
    path("<int:pk>/rechazar/", views.rechazar, name="analisis_rechazar"),
    path("<int:pk>/hallazgo/<int:hid>/decidir/", views.decidir, name="analisis_decidir"),
    path("<int:pk>/cifra/<str:fid>/", views.cifra_origen, name="analisis_cifra"),
    path("<int:pk>/cifra/<str:fid>/pagina.png", views.cifra_pagina, name="analisis_cifra_pagina"),
]
