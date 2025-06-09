from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Roles
from audits.models import Audit


class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
        ("Role", {"fields": ("role",)}),
        ("Configuración de cuenta", {"fields": ("modalidad", "plan")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "is_active",
                    "is_staff",
                    "role",
                    "modalidad",
                    "plan",
                ),
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "role",
        "modalidad",
        "plan",
        "display_assigned_audits",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.role and obj.role.name != "audit_manager":
            # Solo mostrar el campo administrador para usuarios que no son audit_manager
            for fieldset in fieldsets:
                if fieldset[0] == "Configuración de cuenta":
                    fieldset[1]["fields"] = ("modalidad", "plan", "administrador")
                    break
        return fieldsets
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:  # Si estamos creando un nuevo usuario
            form.base_fields["modalidad"].initial = "I"  # Modalidad individual por defecto
            form.base_fields["plan"].initial = "M"  # Plan mensual por defecto
        return form

    def display_assigned_audits(self, obj):
        audits = Audit.objects.filter(assigned_users=obj)
        if audits:
            return "\n".join([f"{a.title} - {a.identidad}" for a in audits])
        else:
            return "No hay auditorias asignadas."

    display_assigned_audits.short_description = "Auditorias Asignadas"


class CustomerRolesAdmin(admin.ModelAdmin):
    model = Roles

    fieldsets = (
        (
            "Nombre del Rol",
            {"fields": ("verbose_name",)},
        ),
        (
            "Clave Nombre del Rol",
            {"fields": ("name",)},
        ),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Roles, CustomerRolesAdmin)
