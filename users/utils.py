from .models import User
from .errors import UsedMailError, UsedUserNameError


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
