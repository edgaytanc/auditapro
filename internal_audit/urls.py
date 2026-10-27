from django.urls import path

from . import views
from .manual_dashboard import dashboard_interna_manual

urlpatterns = [
    # El listado es independiente de Audit y solo contiene datos manuales.
    path("", dashboard_interna_manual, name="dashboard_interna"),
    # NO modificar esta ruta: otros módulos pueden usar el detalle real.
    path("detalle/<int:audit_id>/", views.internal_audit_detail, name="internal_audit_detail"),
]
