from django.contrib import admin
from auditoria.models import AuditMark


@admin.register(AuditMark)
class AuditMarkAdmin(admin.ModelAdmin):
    """
    Administración de marcas de auditoría.

    Sistema actualizado (Cliente 11/2025):
    - 3 columnas principales: Símbolo, Descripción, Papel de Trabajo
    - Categoría movida a sección opcional (legacy)
    - Papel de Trabajo debe estar en MAYÚSCULAS
    """
    list_display = ['symbol', 'description_short', 'work_paper_number',
                   'audit', 'is_active', 'created_at']
    # Removido 'category' del display principal

    list_filter = ['is_active', 'audit']
    # Removido 'category' de filtros principales

    search_fields = ['description', 'work_paper_number', 'symbol', 'audit__title']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Información Básica', {
            'fields': ('audit', 'symbol', 'description'),
            'description': 'Campos principales de la marca de auditoría'
        }),
        ('Papel de Trabajo (⚠️ MAYÚSCULAS)', {
            'fields': ('work_paper_number',),
            'description': (
                '<strong style="color: #856404;">IMPORTANTE:</strong> '
                'El Papel de Trabajo debe estar en MAYÚSCULAS para que el sistema '
                'lo reconozca correctamente.<br>'
                '<strong>Ejemplo correcto:</strong> SUMARIA CAJAS Y BANCOS<br>'
                '<strong>Ejemplo incorrecto:</strong> sumaria cajas y bancos'
            )
        }),
        ('Estado', {
            'fields': ('is_active',),
            'description': 'Marcas inactivas no se inyectan en documentos'
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def description_short(self, obj):
        """Mostrar descripción truncada en la lista"""
        if len(obj.description) > 50:
            return obj.description[:50] + '...'
        return obj.description
    description_short.short_description = 'Descripción'