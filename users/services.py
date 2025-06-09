from .utils import is_email_used, is_username_used
from .errors import (
    EmailNullError,
    FirstNameNullError,
    LastNameNullError,
    PasswordsDoNotMatchesError,
    PasswordsNull,
    UserNameNullError,
    InvalidLoginFields,
    FieldInvalidError,
    FieldNullError,
    UserDoNotExits,
    ValueInvalidError,
    ValueNullError,
    UserUnauthorized,
    InvalidPassword,
)
from django.contrib.auth import get_user_model, authenticate, login
from django.http import HttpRequest
from django.core.exceptions import ValidationError
from django.contrib.auth import update_session_auth_hash

User = get_user_model()


def create_user(
    username: str,
    first_name: str,
    last_name: str,
    email: str,
    password_1: str,
    password_2: str,
):
    try:
        if not username:
            raise UserNameNullError()
        if not first_name:
            raise FirstNameNullError()
        if not last_name:
            raise LastNameNullError()
        if not email:
            raise EmailNullError()
        if not password_1 or not password_2:
            raise PasswordsNull()
        if password_1 != password_2:
            raise PasswordsDoNotMatchesError()

        is_username_used(username)
        is_email_used(email)

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password_1,
        )

        user.save()
    except Exception as e:
        raise e


def update_user(req: HttpRequest, value: str, field: str):
    try:
        user = authenticate(req)
        user = req.user
        if not user:
            raise UserDoNotExits()
        if not user.email:
            EmailNullError()
        if not user.password:
            PasswordsNull()
        if not field:
            raise FieldNullError()
        if not value:
            raise ValueNullError()
        if field.isdigit():
            raise FieldInvalidError()
        if field not in ("username", "email", "first_name", "last_name", "password"):
            raise FieldInvalidError()

        if field == "username":
            is_username_used(value)

        if field == "email":
            is_email_used(value)
        if field == "password":
            user.set_password(value)
            user.save()
            update_session_auth_hash(req, user)
        else:
            setattr(user, field, value)
            user.save()

    except ValidationError as ve:
        raise InvalidPassword()
    except User.DoesNotExist:
        raise UserDoNotExits()
    except Exception as e:
        raise e


def login_user_service(req: HttpRequest, email: str, password: str):
    try:
        if not email:
            raise EmailNullError()

        if not password:
            raise PasswordsNull()

        user = authenticate(req, email=email, password=password)
        if not user:
            raise InvalidLoginFields()

        login(req, user)
        return user
    except Exception as e:
        raise e


def delete_user(req: HttpRequest, email: str, password: str):
    try:
        if not req:
            raise UserUnauthorized()
        if not email:
            raise EmailNullError()
        if not password:
            raise PasswordsNull()
        user = authenticate(req, email=req.user.email, password=password)
        if not user or user.email != email:
            raise InvalidLoginFields()

        user.delete()
    except Exception as e:
        raise e
