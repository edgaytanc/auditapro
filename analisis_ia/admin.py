from django.contrib import admin, messages
from .models import CupoConsultasIA
from .quota import recargar_cinco


@admin.action(description="Restablecer a 5 consultas a los usuarios seleccionados")
def recargar_usuarios(modeladmin, request, queryset):
    for fila in queryset.select_related("usuario"):
        recargar_cinco(fila.usuario)
    modeladmin.message_user(request, "Cupos restablecidos a 5 consultas.", messages.SUCCESS)


@admin.register(CupoConsultasIA)
class CupoConsultasIAAdmin(admin.ModelAdmin):
    list_display = ("usuario", "correo", "restantes", "realizadas", "actualizado")
    search_fields = ("usuario__email", "usuario__username")
    readonly_fields = ("realizadas", "version_cupo", "actualizado")
    list_select_related = ("usuario",)
    actions = [recargar_usuarios]

    @admin.display(description="Correo de la sesión")
    def correo(self, obj):
        return obj.usuario.email or obj.usuario.username
