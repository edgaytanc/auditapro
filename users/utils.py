# Archivo: users/utils.py

from .models import User
from .errors import UsedMailError, UsedUserNameError


# ✅ En lugar de los de arriba, usamos el módulo nuevo y centralizado:
from users.emails import send_activation_email_html as _send_activation_email_html
from users.emails import send_admin_notification_email as _send_admin_notification_email


def is_email_used(email):
    try:
        if User.objects.filter(email=email).exists():
            raise UsedMailError()
    except UsedMailError as e:
        raise e


def is_username_used(username):
    try:
        if User.objects.filter(username=username).exists():
            raise UsedUserNameError()
    except UsedUserNameError as e:
        raise e


def user_to_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": {"name": user.role.name, "verbose_name": user.role.verbose_name},
        "signature": str(user.signature),
        "is_staff": user.is_staff,
        "is_active": user.is_active,
        "date_joined": user.date_joined.isoformat(),
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "is_superuser": user.is_superuser,
    }


# ==========================
#  WRAPPERS DE COMPATIBILIDAD
# ==========================
# Mantienen nombres existentes para no romper imports en vistas/servicios;
# ahora delegan al módulo central users.emails

def send_activation_email(user, password, request):
    """
    [Compatibilidad] Antes estaba implementado directamente aquí.
    Ahora delega al módulo users.emails con plantilla HTML y adjuntos.
    """
    return _send_activation_email_html(user, password, request)


def send_admin_notification_email(creator, new_user):
    """
    [Compatibilidad] Wrapper del nuevo módulo de emails.
    """
    return _send_admin_notification_email(creator, new_user)
