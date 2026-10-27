from datetime import datetime

from django.conf import settings
from django.utils import timezone


def is_valid_date(
    date_str: str,
):
    """
    Valida que una fecha corresponda a alguno
    de los formatos permitidos.
    """

    date_formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%Y-%m",
    ]

    for date_format in date_formats:
        try:
            datetime.strptime(
                date_str,
                date_format,
            )

            return True

        except (
            TypeError,
            ValueError,
        ):
            continue

    return False


def convert_date_str_to_datetime(
    date: str,
) -> datetime:
    """
    Convierte una fecha con formato YYYY-MM-DD
    en un objeto datetime.

    Respeta la configuración USE_TZ del proyecto:

    - USE_TZ=False:
      devuelve un datetime sin zona horaria.

    - USE_TZ=True:
      devuelve un datetime con la zona horaria
      configurada actualmente en Django.
    """

    try:
        converted_date = datetime.strptime(
            date,
            "%Y-%m-%d",
        )

        if settings.USE_TZ:
            return timezone.make_aware(
                converted_date,
                timezone.get_current_timezone(),
            )

        return converted_date

    except (
        TypeError,
        ValueError,
    ):
        raise