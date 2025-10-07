from django.urls import path
from . import views

urlpatterns = [
    # URL para la página de verificación del código 2FA.
    # La lógica de esta vista se implementará en una tarea posterior.
    path("verify-2fa/", views.verify_2fa_view, name="verify_2fa"),
]
