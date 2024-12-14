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
        "display_assigned_audits",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    def display_assigned_audits(self, obj):
        audits = Audit.objects.filter(assigned_users=obj)
        if audits:
            return "\n".join([f"{a.title} - {a.company}" for a in audits])
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
