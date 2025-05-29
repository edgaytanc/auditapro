from django import template
from django.utils import timezone
from django.utils.timezone import localtime
from datetime import timedelta
from typing import Literal


register = template.Library()


@register.filter
def format_date(value):
    now = timezone.now()

    if value.tzinfo is None:
        value = timezone.make_aware(value, timezone.get_current_timezone())

    if now.tzinfo is None:
        now = timezone.make_aware(now, timezone.get_current_timezone())

    value = localtime(value)

    delta = now - value

    if delta.days == 0:
        return f"Hoy, {value.strftime('%H:%M')}"
    elif delta.days == 1:
        return f"Ayer, {value.strftime('%H:%M')}"
    elif 2 <= delta.days <= 3:
        return f"Hace {delta.days} días, {value.strftime('%H:%M')}"
    else:
        return value.strftime("%d de %B del %Y")


@register.filter
def contains_path(value, arg):
    return arg in value


@register.filter(name="getattr")
def getattr_filter(value, arg, default=""):
    return getattr(value, arg, default)


@register.filter(name="format_duration")
def format_duration(
    duration: timedelta,
    show_only: Literal["days", "seconds", "minutes", "hours", "all"] = "all",
):
    if not isinstance(duration, timedelta):
        return str(duration)

    total_seconds = duration.total_seconds()

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    if show_only == "days":
        return f"{int(days)} día{'s' if days != 1 else ''}"

    elif show_only == "hours":
        total_hours = total_seconds / 3600
        return f"{int(total_hours)} hora{'s' if total_hours != 1 else ''}"

    elif show_only == "minutes":
        total_minutes = total_seconds / 60
        return f"{int(total_minutes)} minuto{'s' if total_minutes != 1 else ''}"

    elif show_only == "seconds":
        return f"{int(total_seconds)} segundo{'s' if total_seconds != 1 else ''}"

    parts = []
    if days:
        parts.append(f"{int(days)} día{'s' if days != 1 else ''}")
    if hours and not days:
        parts.append(f"{int(hours)} hora{'s' if hours != 1 else ''}")
    if minutes and not days:
        parts.append(f"{int(minutes)} minuto{'s' if minutes != 1 else ''}")
    if seconds and not days:
        parts.append(f"{int(seconds)} segundo{'s' if seconds != 1 else ''}")

    return ", ".join(parts) if parts else "0 segundos"


@register.filter(name="format_duration_only_number")
def format_duration_only_number(
    duration: timedelta,
    show_only: Literal["days", "seconds", "minutes", "hours", "all"] = "all",
) -> str:
    return format_duration(duration, show_only).split(" ")[0]


@register.filter(name="format_duration_day_number")
def format_duration_day_number(duration: timedelta) -> str:
    return format_duration(duration, "days").split(" ")[0]


@register.filter(name="format_duration_field")
def format_duration_field(
    duration: int, duration_type: Literal["days", "seconds", "minutes", "hours"]
):
    if not isinstance(duration, int):
        duration = int(duration)

    if duration_type == "days":
        return timedelta(days=duration)
    elif duration_type == "seconds":
        return timedelta(seconds=duration)
    elif duration_type == "minutes":
        return timedelta(minutes=duration)
    elif duration_type == "hours":
        return timedelta(hours=duration)


@register.filter(name="format_timedelta_to_microseconds")
def format_timedelta_to_microseconds(duration: timedelta):
    return duration.total_seconds() * 1_000_000
