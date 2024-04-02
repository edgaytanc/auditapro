from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser

class UserAdmin(BaseUserAdmin):
    model = CustomUser
    fieldsets = BaseUserAdmin.fieldsets + (
        (None, {'fields': ('tipo_usuario', 'telefono')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('first_name','last_name','email','tipo_usuario', 'telefono')}),
    )

admin.site.register(CustomUser, UserAdmin)
