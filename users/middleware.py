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


class DemoUserAccessMiddleware:
    """
    Middleware para controlar el acceso de usuarios con rol 'demo'.
    Los usuarios demo tienen acceso limitado al sistema.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Rutas permitidas para usuarios demo
        self.allowed_paths = [
            '/dashboard/',
            '/user/',
            '/logout/',
            '/auditorias/',
            '/financiera/',
            '/interna/',
            '/archivo/',
            '/herramientas/',
            '/proyectos/',
            '/notificaciones/',
            # Añadir aquí otras rutas permitidas para usuarios demo
        ]
        
        # Prefijos de rutas permitidas (para rutas dinámicas)
        self.allowed_prefixes = [
            '/auditoria/',
            '/financiera/',
            '/interna/',
            '/archivo/',
            '/herramientas/',
            '/proyectos/',
            '/notificaciones/',
            '/static/',
            '/media/',
            # Añadir aquí otros prefijos permitidos
        ]
        
    def __call__(self, request):
        # Verificar si el usuario está autenticado y tiene rol demo
        if request.user.is_authenticated and hasattr(request.user, 'role') and request.user.role and request.user.role.name == 'demo':
            # Obtener la ruta actual
            current_path = request.path
            
            # Verificar si la ruta está permitida
            is_allowed = current_path in self.allowed_paths
            
            # Si no está en las rutas exactas, verificar prefijos
            if not is_allowed:
                is_allowed = any(current_path.startswith(prefix) for prefix in self.allowed_prefixes)
            
            # Si la ruta no está permitida, redirigir al dashboard con mensaje
            if not is_allowed:
                messages.warning(
                    request, 
                    "Acceso limitado: Esta funcionalidad no está disponible en la versión demo."
                )
                return redirect('dashboard')
            
        response = self.get_response(request)
        return response
