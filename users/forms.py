from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import (
    UserCreationForm as BaseUserCreationForm,
    UserChangeForm as BaseUserChangeForm,
)


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "assigned_audits",
            "role",
        ]


class UserChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "assigned_audits",
            "role",
        ]
