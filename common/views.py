from django.shortcuts import render


def custom_404(request, exception):
    return render(request, "not-found-page.html", {}, status=404)
