from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from .models import TwoFactorAuth

User = get_user_model()

def verify_2fa_view(request):
    """
    Gestiona la verificación del código de dos factores (2FA).

    En una solicitud GET, muestra el formulario para ingresar el código.
    En una solicitud POST, valida el código y, si es correcto, inicia sesión.
    """
    user_id = request.session.get('pre_2fa_user_id')

    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        messages.error(request, "Ha ocurrido un error inesperado. Por favor, intente iniciar sesión de nuevo.")
        return redirect('login')

    if request.method == 'POST':
        code = request.POST.get('2fa_code')

        if not code:
            messages.error(request, "Por favor, ingrese el código de verificación.")
            return render(request, "mfa/verify_2fa.html")

        try:
            two_factor_auth = TwoFactorAuth.objects.get(user=user, code=code)

            expiration_time = two_factor_auth.created_at + timedelta(minutes=5)
            
            if timezone.now() > expiration_time:
                messages.error(request, "El código de verificación ha expirado. Por favor, intente iniciar sesión de nuevo.")
                two_factor_auth.delete()
                return redirect('login')

            
            # Le decimos explícitamente a Django qué backend de autenticación usar
            # para este usuario, ya que lo obtuvimos directamente de la base de datos.
            user.backend = 'users.backends.EmailBackend'

            # Ahora la función login() sabe qué backend utilizar.
            login(request, user)
            
            two_factor_auth.delete()
            del request.session['pre_2fa_user_id']
            
            messages.success(request, f"¡Bienvenido de nuevo, {user.get_full_name() or user.username}!")
            return redirect('home')

        except TwoFactorAuth.DoesNotExist:
            messages.error(request, "El código ingresado es incorrecto.")
            return render(request, "mfa/verify_2fa.html")

    return render(request, "mfa/verify_2fa.html")

def resend_2fa_code(request):
    """
    Reenvía el código de verificación al usuario.
    """
    user_id = request.session.get('pre_2fa_user_id')

    if not user_id:
        return redirect('login')

    try:
        user = User.objects.get(id=user_id)
        from .utils import send_2fa_code
        try:
            send_2fa_code(user)
            messages.success(request, "Se ha enviado un nuevo código de verificación a su correo.")
        except Exception as e:
            # En entorno local/desarrollo es común que falle el envío de correos si no está configurado SMTP.
            # Capturamos el error para no mostrar una pantalla de error 500.
            messages.error(request, "No se pudo enviar el correo de verificación. Por favor, intente más tarde o contacte a soporte.")
            print(f"Error al enviar correo 2FA: {e}")
            
    except User.DoesNotExist:
        pass
    
    return redirect('verify_2fa')