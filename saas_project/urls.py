from django.contrib import admin
from django.urls import path, include
from common.views import soporte
from analisis_ia.views import audita_analisis, enviar_consulta
from analisis_ia.admin_views import administrar_cupos
from notifications import urls as notifications_urls
from users import urls as users_urls
from audits import urls as audits_urls
from management_auditors import urls as management_auditors_urls
from archivo import urls as archivo_urls
from tools import urls as tools_urls
from auditoria import urls as auditoria_urls
from user_management import urls as user_management_urls

urlpatterns = [
    path("soporte/", soporte, name="soporte"),
    # Consultas reales Claude y pantalla de cupos separadas de auditorías y Superadmin.
    path("audita-analisis/", audita_analisis, name="audita_analisis"),
    path("audita-analisis/consultar/", enviar_consulta, name="audita_analisis_consultar"),
    path("usuarios/audita-analisis-cupos/", administrar_cupos, name="audita_analisis_cupos"),
    path("admin/", admin.site.urls, name="admin"),
    path("", include(users_urls)),
    path("notificaciones/", include(notifications_urls)),
    path("planes/", include("planes.urls")),
    path("videos-guias/", include("videos_guias.urls")),
    path("auditorias/", include(audits_urls)),
    path("gestionar_auditores/", include(management_auditors_urls)),
    path("archivo_permanente/", include(archivo_urls)),
    path("herramientas/", include(tools_urls)),
    path("auditoria/", include(auditoria_urls)),
    path("usuarios/", include(user_management_urls)),
    path("mfa/", include("mfa.urls")),  # Rutas para la autenticación de dos factores
    
]