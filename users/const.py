from .errors import (
    EmailNullError,
    FirstNameNullError,
    InvalidLoginFields,
    LastNameNullError,
    PasswordsDoNotMatchesError,
    PasswordsNull,
    UsedMailError,
    UsedUserNameError,
    UserDoNotExits,
    UserNameNullError,
    FieldInvalidError,
    FieldNullError,
    ValueInvalidError,
    ValueNullError,
    UserUnauthorized,
    InvalidPassword,
)

from common.constants import ERROR_INSTANCES


ROLE_CHOICES = [
    ("auditor", "Auditor"),
    ("supervisor", "Supervisor"),
    ("audit_manager", "Jefe de Auditoría"),
]

USER_ERROR_INSTANCES = (
    UserNameNullError,
    UsedUserNameError,
    EmailNullError,
    UsedMailError,
    PasswordsNull,
    PasswordsDoNotMatchesError,
    FirstNameNullError,
    LastNameNullError,
    InvalidLoginFields,
    UserDoNotExits,
    FieldInvalidError,
    FieldNullError,
    ValueInvalidError,
    ValueNullError,
    UserUnauthorized,
    InvalidPassword,
) + ERROR_INSTANCES

USER_CLIENT_FIELDS = (
    ("username", "Nombre de Usuario"),
    ("first_name", "Nombre Completo"),
    ("last_name", "Apellidos"),
    ("email", "Correo Electrónico"),
)
