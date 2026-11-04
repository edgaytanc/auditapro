from django.contrib import admin

from .models import BitacoraAnalisis, CifraAnalisis, CorridaAnalisis, DocumentoAnalisis, HallazgoAnalisis, VersionPapel


class SoloLectura(admin.ModelAdmin):
    """La bitácora y los resultados no se editan a mano desde el administrador."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CorridaAnalisis)
class CorridaAdmin(SoloLectura):
    list_display = ("pk", "titulo", "audit", "creado_por", "estado", "revision", "creado_en")
    list_filter = ("estado", "revision")
    search_fields = ("titulo", "audit__title")
    exclude = ("tablas",)


@admin.register(DocumentoAnalisis)
class DocumentoAdmin(SoloLectura):
    list_display = ("nombre_original", "corrida", "rol", "formato", "tamano", "estado_lectura")


@admin.register(HallazgoAnalisis)
class HallazgoAdmin(SoloLectura):
    list_display = ("codigo", "corrida", "agente", "alerta", "decision")


@admin.register(CifraAnalisis)
class CifraAdmin(SoloLectura):
    list_display = ("fid", "corrida", "valor", "documento_nombre", "estado")


@admin.register(VersionPapel)
class VersionAdmin(SoloLectura):
    list_display = ("nombre", "corrida", "numero", "creado_en")


@admin.register(BitacoraAnalisis)
class BitacoraAdmin(SoloLectura):
    list_display = ("creado_en", "corrida", "usuario", "accion")

    def has_delete_permission(self, request, obj=None):
        return False
