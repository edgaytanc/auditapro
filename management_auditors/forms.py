from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from users.models import Roles

User = get_user_model()

class AuditorCreationForm(UserCreationForm):
    """
    Formulario para crear usuarios auditores desde el panel de gestión de auditores.
    Solo incluye los campos necesarios para un auditor.
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label="Nombre")
    last_name = forms.CharField(max_length=30, required=True, label="Apellido")

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def save(self, commit=True, admin_user=None):
        # Guardar el usuario con los datos del formulario
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Asignar modalidad grupal
        user.modalidad = 'G'
        
        # Asignar el administrador
        if admin_user:
            user.administrador = admin_user
        
        # Asignar el rol de auditor
        auditor_role, _ = Roles.objects.get_or_create(name="auditor", verbose_name="Auditor")
        user.role = auditor_role
        
        if commit:
            user.save()
        
        return user
