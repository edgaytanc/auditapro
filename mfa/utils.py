# Archivo: mfa/utils.py

import random
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import TwoFactorAuth
from users.models import User

def send_2fa_code(user: User):
    """
    Genera un código de 6 dígitos, lo guarda en la base de datos
    y lo envía al correo electrónico del usuario.
    """
    # Genera un código aleatorio de 6 dígitos
    code = str(random.randint(100000, 999999))

    # Guarda o actualiza el código en la base de datos para el usuario
    # El objeto se crea si no existe, o se actualiza si ya existe.
    TwoFactorAuth.objects.update_or_create(
        user=user,
        defaults={'code': code}
    )

    # Prepara el contexto para las plantillas de correo
    context = {
        'user': user,
        'code': code,
    }

    # Renderiza las plantillas de correo (HTML y texto plano)
    email_html_message = render_to_string('mfa/email/2fa_code.html', context)
    email_plaintext_message = render_to_string('mfa/email/2fa_code.txt', context)

    # Envía el correo electrónico
    send_mail(
        # Asunto del correo
        "Tu código de verificación para AuditaPro",
        # Mensaje de texto plano (para clientes de correo que no soportan HTML)
        email_plaintext_message,
        # Correo remitente (tomado de settings.py)
        settings.DEFAULT_FROM_EMAIL,
        # Lista de destinatarios
        [user.email],
        # Mensaje en formato HTML
        html_message=email_html_message,
        fail_silently=False,
    )