from django import template

register = template.Library()

@register.filter
def split(value, delimiter=","):
    """Divide una cadena usando el delimitador especificado."""
    if not value:
        return []
    return [v.strip() for v in value.split(delimiter)]
