from django.contrib import admin
from .models import Audit


class AuditAdmin(admin.ModelAdmin):
    model = Audit
    fieldsets = (
        (
            "Datos de la auditoria",
            {
                "fields": (
                    "title",
                    "description",
                    "company",
                    "created_at",
                )
            },
        ),
        (
            "Jefe de auditoria",
            {"fields": ("audit_manager",)},
        ),
        (
            "Usuarios asignados para esta auditoria",
            {"fields": ("assigned_users",)},
        ),
    )


admin.site.register(Audit, AuditAdmin)
