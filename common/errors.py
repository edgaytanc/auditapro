class InvalidIdError(Exception):
    def __init__(self):
        super().__init__("El Identificador Único ingresado es inválido.")
