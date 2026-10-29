from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_GET


def custom_404(request, exception):
    return render(request, "not-found-page.html", {}, status=404)


@login_required
@require_GET
def soporte(request):
    """Centro de ayuda, disponible para usuarios que han iniciado sesion."""
    return render(request, "common/soporte.html")
