from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

class CustomLoginView(LoginView):
    template_name = 'login.html'

    # def get_success_url(self):
    #     return reverse_lazy('home')  # O la URL que prefieras

@login_required
def home(request):
    # Asegúrate de que 'get_full_name()' es un método válido de tu 'CustomUser'
    return render(request, 'index.html', {'nombre_usuario': request.user.username})


