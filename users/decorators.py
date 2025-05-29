from django.http import Http404
from functools import wraps


def superuser_required(view_func):
    """
    Decorador para restringir el acceso a vistas a solo superusuarios.
    Muestra una página de error 404 si el usuario no es un superusuario.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            raise Http404("La página que estás buscando no existe.")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
