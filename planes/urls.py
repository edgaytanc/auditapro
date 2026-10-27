from django.urls import path
from . import views

app_name = "planes"

urlpatterns = [
    path("mejorar/", views.mejorar_plan, name="mejorar"),
    path("renovacion/", views.renovacion, name="renovacion"),
    path("comprar/<slug:plan>/", views.comprar, name="comprar"),
]
