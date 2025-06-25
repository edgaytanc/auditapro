from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from users.models import User
import logging

logger = logging.getLogger(__name__)

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
            '/logout/',
            '/user/',
            '/financiera/',
            '/auditorias/',
            '/interna/',
            '/archivo/',
            '/herramientas/',
            '/proyectos/',
            '/notificaciones/',
            '/api/notificaciones/',
        ]
        
        # Prefijos de rutas permitidas (para rutas dinámicas)
        self.allowed_prefixes = [
            '/static/',
            '/media/',
            '/api/financiera/',
            '/api/auditorias/',
            '/api/interna/',
            '/api/archivo/',
            '/api/herramientas/',
            '/api/proyectos/',
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


class DemoUserExpirationMiddleware:
    """
    Middleware que verifica y da de baja automáticamente a los usuarios con plan DEMO
    que fueron creados hace más de 48 horas.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Ejecutamos una vez al iniciar el servidor
        self._check_expired_demo_users()
        # Última vez que se ejecutó la verificación
        self.last_check = timezone.now()
        # Intervalo mínimo entre verificaciones (1 hora)
        self.check_interval = timezone.timedelta(hours=1)
        
    def __call__(self, request):
        # Verificar usuarios demo expirados periódicamente (no en cada petición)
        current_time = timezone.now()
        if current_time - self.last_check > self.check_interval:
            self._check_expired_demo_users()
            self.last_check = current_time
            
        response = self.get_response(request)
        return response
    
    def _check_expired_demo_users(self):
        """Verifica y da de baja a los usuarios demo expirados"""
        try:
            # Calcular la fecha límite (48 horas atrás desde ahora)
            expiration_time = timezone.now() - timezone.timedelta(hours=120)
            
            # Buscar usuarios con plan DEMO que no estén dados de baja y que fueron creados antes del tiempo límite
            expired_demo_users = User.objects.filter(
                Q(plan='DEMO') & Q(is_deleted=False) & Q(date_joined__lt=expiration_time)
            )
            
            count = 0
            for user in expired_demo_users:
                try:
                    # Marcar como eliminado y guardar la fecha de eliminación
                    user.is_deleted = True
                    user.deleted_at = timezone.now()
                    user.save(update_fields=['is_deleted', 'deleted_at'])
                    
                    logger.info(f"Usuario demo expirado dado de baja automáticamente: {user.username} (ID: {user.id})")
                    count += 1
                except Exception as e:
                    logger.error(f"Error al dar de baja usuario demo expirado {user.username}: {str(e)}")
            
            if count > 0:
                logger.info(f"Total de usuarios demo expirados dados de baja: {count}")
        except Exception as e:
            logger.error(f"Error al verificar usuarios demo expirados: {str(e)}")
