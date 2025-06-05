from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse


class UserDeactivationMiddleware:
    """
    Middleware para verificar si un usuario está dado de baja.
    Si el usuario está dado de baja, se le cierra la sesión y se le redirige a la página de login.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Verificar si el usuario está autenticado
        if request.user.is_authenticated:
            # Verificar si el usuario tiene el atributo is_deleted y está dado de baja
            if hasattr(request.user, 'is_deleted') and request.user.is_deleted:
                # Guardar el nombre de usuario para el mensaje
                username = request.user.username
                
                # Cerrar sesión
                logout(request)
                
                # Mostrar mensaje solo si el sistema de mensajes está disponible
                if hasattr(request, '_messages'):
                    messages.error(
                        request, 
                        f"La cuenta '{username}' ha sido dada de baja. Por favor, contacta con el administrador si crees que esto es un error."
                    )
                
                # Redirigir al login
                return redirect('login')  # Asegúrate de que 'login' es el nombre de tu URL de login
            
        response = self.get_response(request)
        return response
