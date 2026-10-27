from django.urls import path

from . import views

app_name = "videos_guias"

urlpatterns = [
    path("", views.index, name="index"),
    path("guias/<slug:slug>/", views.guide_pdf, name="guia"),
]
