from functools import wraps


def add_breadcrumbs(breadcrumbs):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Ejecuta la vista y recibe la respuesta
            response = view_func(request, *args, **kwargs)

            # Asegúrate de que la respuesta sea un render de plantilla con contexto
            if isinstance(response, dict):
                # Agrega los breadcrumbs al contexto de la vista
                response["breadcrumbs"] = breadcrumbs
            return response

        return _wrapped_view

    return decorator
