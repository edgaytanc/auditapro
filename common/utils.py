from datetime import datetime
import pytz


def is_valid_date(date_str: str):
    date_formats = [
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d",
        "%Y-%m",
    ]
    for fmt in date_formats:
        try:
            datetime.strptime(date_str, fmt)
            return True
        except ValueError:
            continue

    return False


def convert_date_str_to_datetime(date: str) -> datetime:
    try:
        # Convierte el string a datetime naive
        naive_datetime = datetime.strptime(date, "%Y-%m-%d")
        # Agrega la zona horaria UTC al datetime
        aware_datetime = naive_datetime.replace(tzinfo=pytz.UTC)
        return aware_datetime
    except Exception as e:
        raise e
