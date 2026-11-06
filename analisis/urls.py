from django.urls import path

from . import views, views_flujo as vf

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
    # fase 2: hallazgos → plantillas → revisión → informe, y Monitoreo Continuo
    path("<int:pk>/enviar-hallazgos/", vf.enviar_hallazgos, name="analisis_enviar_hallazgos"),
    path("proyecto/<int:audit_id>/hallazgos/", vf.hallazgos_proyecto, name="analisis_hallazgos"),
    path("proyecto/<int:audit_id>/hallazgos/a-revision/", vf.a_revision, name="analisis_a_revision"),
    path("proyecto/<int:audit_id>/hallazgos/<int:hid>/decidir/", vf.decidir_hallazgo, name="analisis_decidir_hallazgo"),
    path("proyecto/<int:audit_id>/hallazgos/<int:hid>/reabrir/", vf.reabrir_hallazgo, name="analisis_reabrir_hallazgo"),
    path("proyecto/<int:audit_id>/hallazgos/informe/", vf.generar_informe, name="analisis_generar_informe"),
    path("proyecto/<int:audit_id>/hallazgos/sincronizar/", vf.sincronizar, name="analisis_sincronizar"),
    path("proyecto/<int:audit_id>/archivo/<int:pk>/", vf.descargar_archivo, name="analisis_archivo"),
    path("proyecto/<int:audit_id>/monitoreo/", vf.monitoreo_panel, name="analisis_monitoreo"),
    path("proyecto/<int:audit_id>/monitoreo/excel/", vf.monitoreo_descarga_panel, name="analisis_monitoreo_excel"),
    path("proyecto/<int:audit_id>/monitoreo/<int:pk>/accion/", vf.monitoreo_accion, name="analisis_monitoreo_accion"),
    path("proyecto/<int:audit_id>/monitoreo/<int:pk>/descargar/<str:formato>/", vf.monitoreo_descarga, name="analisis_monitoreo_descarga"),
]
