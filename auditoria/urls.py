from django.urls import path
from . import views
from .utils.import_utils import importar_cuentas_contables
from .utils.export_utils import export_cuentas_contables

urlpatterns = [
    path('', views.auditorias_view, name='auditorias'),
    path('financiera/', views.auditoria_financiera_view, name='auditoria_financiera'),
    path('interna/', views.auditoria_interna_view, name='auditoria_interna'),
    path('detalle/<int:audit_id>/', views.auditoria_detalle_view, name='auditoria_detalle'),
    path('download/<int:audit_id>/<path:folder>/<str:filename>/', views.download_document, name='download_document'),
    path('download/<int:audit_id>/<str:pattern>/', views.download_document_by_pattern, name='download_document_by_pattern'),
    path('detalle/<int:audit_id>/exportar/<str:tipo>/', export_cuentas_contables, name='export_cuentas_contables'),
    path('auditoria/detalle/<int:audit_id>/importar-cuentas/', importar_cuentas_contables, name='importar_cuentas_contables'),
]