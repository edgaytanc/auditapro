from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Roles
from audits.models import Audit


class CustomUserAdmin(UserAdmin):
    model = User

    # 🔹 CONFIGURACIÓN DE CAMPOS
        
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

        #  Bloque de Rol (agregamos 'socio' aquí)
        (
            "Role",
            {
                "fields": ("role", "socio"),  # <-- NUEVO CAMPO (con visibilidad controlada más abajo)
            },
        ),

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

        #  Mostramos la columna "socio" solo si existe en el modelo
        "socio",
    )

    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("email",)

    #  LÓGICA DE VISIBILIDAD Y RESTRICCIONES

    def get_fieldsets(self, request, obj=None):
        """
        Personaliza los fieldsets visibles dependiendo del tipo de usuario y del rol.
        """
        fieldsets = super().get_fieldsets(request, obj)

        #  Si el rol no es 'audit_manager', mostramos el campo 'administrador'
        if obj and obj.role and obj.role.name != "audit_manager":
            for fieldset in fieldsets:
                if fieldset[0] == "Configuración de cuenta":
                    fieldset[1]["fields"] = ("modalidad", "plan", "administrador")
                    break

        #  Si el usuario logueado NO es superadmin → ocultamos el campo 'socio'
        if not request.user.is_superuser:
            updated_fieldsets = []
            for title, opts in fieldsets:
                if "fields" in opts and "socio" in opts["fields"]:
                    # Eliminamos el campo socio de la vista
                    fields = tuple(f for f in opts["fields"] if f != "socio")
                    updated_fieldsets.append((title, {**opts, "fields": fields}))
                else:
                    updated_fieldsets.append((title, opts))
            return updated_fieldsets

        return fieldsets


    def get_readonly_fields(self, request, obj=None):
        """
        El campo 'socio' solo puede ser modificado por el superadmin.
        Otros usuarios (aunque tengan permisos de admin) lo verán como lectura o no lo verán.
        """
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.append("socio")
        return readonly


    def get_form(self, request, obj=None, **kwargs):
        """
        Define valores iniciales para ciertos campos al crear un usuario.
        """
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            form.base_fields["modalidad"].initial = "I"
            form.base_fields["plan"].initial = "M"
        return form


    # COLUMNAS PERSONALIZADAS

    def display_assigned_audits(self, obj):
        """
        Muestra las auditorías asignadas al usuario directamente en el listado del admin.
        """
        audits = Audit.objects.filter(assigned_users=obj)
        if audits:
            return "\n".join([f"{a.title} - {a.identidad}" for a in audits])
        return "No hay auditorías asignadas."

    display_assigned_audits.short_description = "Auditorías Asignadas"



# REGISTRO DE MODELOS EN EL ADMIN


class CustomerRolesAdmin(admin.ModelAdmin):
    model = Roles
    fieldsets = (
        ("Nombre del Rol", {"fields": ("verbose_name",)}),
        ("Clave Nombre del Rol", {"fields": ("name",)}),
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(Roles, CustomerRolesAdmin)
