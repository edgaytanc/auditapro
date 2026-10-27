from django.urls import path

from . import views
from .views import document_generation, muestreo_views, parametros_views
from .api import template_creator_views
from .utils.export_utils import (
    export_cuentas_contables,
)
from .utils.import_utils import (
    importar_cuentas_contables,
)
from .views import audit_mark_views


urlpatterns = [
    path(
        "",
        views.auditorias_view,
        name="auditorias",
    ),
    path(
        "financiera/",
        views.auditoria_financiera_view,
        name="auditoria_financiera",
    ),
    path(
        "interna/",
        views.auditoria_interna_view,
        name="auditoria_interna",
    ),
    path(
        "revisoria/",
        views.auditoria_revisoria_view,
        name="auditoria_revisoria",
    ),
    path(
        "detalle/<int:audit_id>/",
        views.auditoria_detalle_view,
        name="auditoria_detalle",
    ),
    path(
        (
            "download/<int:audit_id>/"
            "<path:folder>/<str:filename>/"
        ),
        views.download_document,
        name="download_document",
    ),
    path(
        (
            "download/<int:audit_id>/"
            "<str:pattern>/"
        ),
        views.download_document_by_pattern,
        name="download_document_by_pattern",
    ),
    path(
        (
            "detalle/<int:audit_id>/"
            "exportar/<str:tipo>/"
        ),
        export_cuentas_contables,
        name="export_cuentas_contables",
    ),
    path(
        (
            "auditoria/detalle/<int:audit_id>/"
            "importar-cuentas/"
        ),
        importar_cuentas_contables,
        name="importar_cuentas_contables",
    ),

    # Marcas de auditoría
    path(
        "audit/<int:audit_id>/upload-marks/",
        audit_mark_views.upload_audit_marks,
        name="upload_audit_marks",
    ),
    path(
        "audit-mark-template/download/",
        audit_mark_views.download_audit_mark_template,
        name="download_audit_mark_template",
    ),

    # API de creación de plantillas
    path(
        "api/validate-workbook-name/",
        template_creator_views.validate_workbook_name,
        name="api_validate_workbook_name",
    ),
    path(
        "api/validate-template-config/",
        template_creator_views.validate_template_config,
        name="api_validate_template_config",
    ),
    path(
        "api/symbols/library/",
        template_creator_views.get_symbols_library,
        name="api_get_symbols_library",
    ),
    path(
        "api/generate-template/",
        template_creator_views.generate_template,
        name="api_generate_template",
    ),
    path(
        "api/audit/<int:audit_id>/marks/",
        template_creator_views.get_audit_marks,
        name="api_get_audit_marks",
    ),

    # Funcionalidades recuperadas de auditapro-develop; sin reemplazar rutas v2.
    path("detalle/<int:audit_id>/generar-modal/", document_generation.generar_documento_modal, name="generar_documento_modal"),
    path("detalle/<int:audit_id>/obtener-carpetas/", document_generation.obtener_carpetas_auditoria, name="obtener_carpetas_auditoria"),
    path("detalle/<int:audit_id>/obtener-documentos/<path:carpeta_nombre>/", document_generation.obtener_documentos_auditoria, name="obtener_documentos_auditoria"),
    path("detalle/<int:audit_id>/descargar-documento/", document_generation.descargar_documento_auditoria, name="descargar_documento_auditoria"),
    path("muestreo/<int:audit_id>/", muestreo_views.muestreo_page, name="muestreo_page"),
    path("muestreo/<int:audit_id>/calcular/", muestreo_views.muestreo_calcular, name="muestreo_calcular"),
    path("muestreo/<int:audit_id>/descargar/", muestreo_views.muestreo_descargar, name="muestreo_descargar"),
    path("muestreo/<int:audit_id>/importar-datos/", muestreo_views.muestreo_importar_datos, name="muestreo_importar_datos"),
    path("muestreo/<int:audit_id>/formato-datos/", muestreo_views.muestreo_formato_datos, name="muestreo_formato_datos"),
    path("muestreo/<int:audit_id>/mum/", muestreo_views.muestreo_mum, name="muestreo_mum"),
    path("muestreo/<int:audit_id>/motor/", muestreo_views.muestreo_page_motor, name="muestreo_page_motor"),
    path("detalle/<int:audit_id>/anios/", parametros_views.anios_auditoria, name="anios_auditoria"),
    path("detalle/<int:audit_id>/referencia/", parametros_views.referencia_papel, name="referencia_papel"),
]
