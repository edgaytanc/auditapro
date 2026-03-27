from django.urls import path
from . import views
from .utils.import_utils import importar_cuentas_contables
from .utils.export_utils import export_cuentas_contables
from .views import audit_mark_views
from .views import audit_views
from .api import template_creator_views

urlpatterns = [
    path('', views.auditorias_view, name='auditorias'),
    path('financiera/', views.auditoria_financiera_view, name='auditoria_financiera'),
    path('interna/', views.auditoria_interna_view, name='auditoria_interna'),
    path('revisoria/', views.auditoria_revisoria_view, name='auditoria_revisoria'),
    path('detalle/<int:audit_id>/', views.auditoria_detalle_view, name='auditoria_detalle'),
    path('download/<int:audit_id>/<path:folder>/<str:filename>/', views.download_document, name='download_document'),
    path('download/<int:audit_id>/<str:pattern>/', views.download_document_by_pattern, name='download_document_by_pattern'),
    path('detalle/<int:audit_id>/exportar/<str:tipo>/', export_cuentas_contables, name='export_cuentas_contables'),
    path('auditoria/detalle/<int:audit_id>/importar-cuentas/', importar_cuentas_contables, name='importar_cuentas_contables'),

    # Audit Mark Routes
    path('audit/<int:audit_id>/upload-marks/', audit_mark_views.upload_audit_marks, name='upload_audit_marks'),
    path('audit-mark-template/download/', audit_mark_views.download_audit_mark_template, name='download_audit_mark_template'),

    # Template Creator API Routes
    path('api/validate-workbook-name/', template_creator_views.validate_workbook_name, name='api_validate_workbook_name'),
    path('api/validate-template-config/', template_creator_views.validate_template_config, name='api_validate_template_config'),
    path('api/symbols/library/', template_creator_views.get_symbols_library, name='api_get_symbols_library'),
    path('api/generate-template/', template_creator_views.generate_template, name='api_generate_template'),
    path('api/audit/<int:audit_id>/marks/', template_creator_views.get_audit_marks, name='api_get_audit_marks'),
    
    # Generate Document Routes
    path("generate/<int:audit_id>/", audit_views.generate_audit_document, name="generate_audit_document"),
    path("detalle/<int:audit_id>/generar-modal/", audit_views.generar_documento_modal, name="generar_documento_modal"),
    path('detalle/<int:audit_id>/obtener-carpetas/', audit_views.obtener_carpetas_auditoria, name='obtener_carpetas_auditoria'),
    path("detalle/<int:audit_id>/obtener-documentos/<path:carpeta_nombre>/", audit_views.obtener_documentos_auditoria, name="obtener_documentos_auditoria"),
    path("detalle/<int:audit_id>/descargar-documento/", audit_views.descargar_documento_auditoria, name="descargar_documento_auditoria"),
]