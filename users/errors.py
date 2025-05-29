class UsedMailError(Exception):
    def __init__(self):
        super().__init__(
            "El correo electrónico ya está registrado, por favor ingrese otro."
        )


class UsedUserNameError(Exception):
    def __init__(self):
        super().__init__(
            "El nombre de usuario ya está registrado, por favor seleccione otro."
        )


class PasswordsDoNotMatchesError(Exception):
    def __init__(self):
        super().__init__("Las contraseñas no coinciden.")


class FirstNameNullError(Exception):
    def __init__(self):
        super().__init__("El primer nombre no puede estar vacío.")


class LastNameNullError(Exception):
    def __init__(self):
        super().__init__("El apellido no puede estar vacío.")


class EmailNullError(Exception):
    def __init__(self):
        super().__init__("El correo electrónico no puede estar vacío.")


class UserNameNullError(Exception):
    def __init__(self):
        super().__init__("El nombre de usuario no puede estar vacío.")


class PasswordsNull(Exception):
    def __init__(self):
        super().__init__("Las contraseñas no pueden estar vacías.")


class InvalidLoginFields(Exception):
    def __init__(self):
        super().__init__("Alguno de los campos ingresados es inváldo.")


class UserDoNotExits(Exception):
    def __init__(self):
        super().__init__("El usuario ingresado no existe.")


class FieldNullError(Exception):
    def __init__(self):
        super().__init__("El campo a actualizar no puede estar vacío.")


class ValueNullError(Exception):
    def __init__(self):
        super().__init__("El valor a actualizar no puede estar vacío.")


class FieldInvalidError(Exception):
    def __init__(self):
        super().__init__("El campo a actualizar es inválido.")


class ValueInvalidError(Exception):
    def __init__(self):
        super().__init__("El valor a actualizar es inválido.")


class UserUnauthorized(Exception):
    def __init__(self):
        super().__init__("Usted no está autorizado para realizar esta acción.")


class InvalidPassword(Exception):
    def __init__(self):
        super().__init__(
            "La contraseña ingresada no cumple con las validaciones necesarias."
        )


class AuditorNullError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__("El Auditor ingresado no puede estar vacío")


class AuditorInvalidError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__("El auditor ingresado no existe o es inválido")
