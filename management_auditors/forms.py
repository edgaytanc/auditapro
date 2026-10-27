from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from users.models import Roles


User = get_user_model()


MANAGED_ROLE_CHOICES = (
    ("auditor", "Auditor"),
    ("supervisor", "Supervisor"),
    ("readonly", "Solo Lectura"),
)


def get_managed_role(role_name):
    """
    Obtiene o crea uno de los roles administrables.

    Se utiliza filter().first() en lugar de get_or_create()
    para evitar errores si la base de datos contiene roles
    duplicados creados anteriormente.
    """

    role_labels = dict(MANAGED_ROLE_CHOICES)

    if role_name not in role_labels:
        raise ValueError(
            f"El rol '{role_name}' no es un rol administrable."
        )

    role = (
        Roles.objects
        .filter(name=role_name)
        .order_by("id")
        .first()
    )

    expected_verbose_name = role_labels[role_name]

    if role is None:
        role = Roles.objects.create(
            name=role_name,
            verbose_name=expected_verbose_name,
        )

    elif role.verbose_name != expected_verbose_name:
        role.verbose_name = expected_verbose_name

        role.save(
            update_fields=[
                "verbose_name",
            ]
        )

    return role


class AuditorCreationForm(UserCreationForm):
    """
    Crea integrantes pertenecientes al equipo
    de un Jefe de Auditoría.
    """

    email = forms.EmailField(
        required=True,
        label="Correo electrónico",
    )

    first_name = forms.CharField(
        max_length=30,
        required=True,
        label="Nombre",
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        label="Apellido",
    )

    system_role = forms.ChoiceField(
        choices=MANAGED_ROLE_CHOICES,
        required=True,
        initial="auditor",
        label="Rol del sistema",
    )

    class Meta:
        model = User

        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "system_role",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data[
            "email"
        ].strip().lower()

        if User.objects.filter(
            email__iexact=email,
        ).exists():
            raise forms.ValidationError(
                "Ya existe un usuario registrado con este correo."
            )

        return email

    def save(
        self,
        commit=True,
        admin_user=None,
    ):
        if admin_user is None:
            raise ValueError(
                "Se requiere el Jefe de Auditoría "
                "para crear el usuario."
            )

        user = super().save(
            commit=False,
        )

        user.email = self.cleaned_data[
            "email"
        ]

        user.first_name = self.cleaned_data[
            "first_name"
        ].strip()

        user.last_name = self.cleaned_data[
            "last_name"
        ].strip()

        user.modalidad = "G"
        user.administrador = admin_user
        user.is_active = True
        user.is_deleted = False

        selected_role_name = self.cleaned_data[
            "system_role"
        ]

        user.role = get_managed_role(
            selected_role_name
        )

        if commit:
            user.save()

        return user


class AuditorRoleUpdateForm(forms.Form):
    """
    Permite cambiar el rol operativo de un integrante
    perteneciente al equipo del Jefe de Auditoría.
    """

    system_role = forms.ChoiceField(
        choices=MANAGED_ROLE_CHOICES,
        required=True,
        label="Rol del sistema",
    )

    def save(self, user):
        selected_role_name = self.cleaned_data[
            "system_role"
        ]

        selected_role = get_managed_role(
            selected_role_name
        )

        user.role = selected_role

        user.save(
            update_fields=[
                "role",
            ]
        )

        return user