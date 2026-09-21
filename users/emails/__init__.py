# Archivo: users/emails/__init__.py
# Módulo centralizado para el envío de correos (HTML + adjuntos)

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

import os
import logging

logger = logging.getLogger(__name__)

# --- Rutas y constantes auxiliares ---
ATTACH_DIR = getattr(
    settings,
    "EMAIL_ATTACHMENTS_DIR",
    os.path.join(settings.BASE_DIR, "static", "envio_correo"),
)
NOTIFY_EMAIL = getattr(
    settings, "AUDITA_NOTIFICATIONS_EMAIL", "sistemaaudita@gmail.com"
)

# Archivos a adjuntar al usuario nuevo
DEFAULT_ATTACHMENTS = [
    os.path.join(ATTACH_DIR, "GUIA USO DEL SISTEMA AUDITA.pdf"),
    os.path.join(ATTACH_DIR, "ESTADOS-FINANCIEROS USAR PARA IMPORTAR.xlsx"),
]

VIDEO_URL = "https://drive.google.com/file/d/106fD9D6sVN1IwZTFlNfZdkZ5aUdfWr21/view"
SUPPORT_EMAIL = "sistemaaudita@gmail.com"


def _safe_attach_files(email_obj, paths):
    """Adjunta archivos si existen; registra warnings si faltan."""
    for fp in paths or []:
        try:
            if os.path.exists(fp):
                email_obj.attach_file(fp)
            else:
                logger.warning(f"[EMAIL] Archivo adjunto no encontrado: {fp}")
        except Exception as e:
            logger.error(f"[EMAIL] Error adjuntando archivo {fp}: {e}", exc_info=True)


def send_activation_email_html(user, password, request):
    """
    Envía correo HTML de activación + adjuntos + texto alternativo.
    Incluye credenciales del usuario y enlace de activación.
    """
    # 1) Construir enlace de activación
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    activation_link = request.build_absolute_uri(
        reverse("activate_account", kwargs={"uidb64": uid, "token": token})
    )

    # 2) Construir URL del sistema
    base_url = getattr(settings, "BASE_URL", None)
    if base_url:
        base_url = base_url.rstrip("/")
    else:
        base_url = request.build_absolute_uri("/").rstrip("/")
    system_url = f"{base_url}/login"

    subject = "Acceso al Sistema Audita"

    context = {
        "user": user,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.email,
        "password": password,
        "activation_link": activation_link,
        "video_url": VIDEO_URL,
        "support_email": SUPPORT_EMAIL,
        "system_url": system_url,
    }

    html_body = render_to_string("users/welcome_email.html", context)
    text_body = strip_tags(html_body)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    msg.attach_alternative(html_body, "text/html")

    _safe_attach_files(msg, DEFAULT_ATTACHMENTS)
    msg.send(fail_silently=False)
    return True


def send_admin_notification_email(creator, new_user):
    """
    Notificación interna para el correo del sistema.
    Indica quién creó al usuario y los datos del nuevo usuario.
    """
    subject = "Nuevo usuario creado por un socio"
    body = (
        "Se ha creado un nuevo usuario desde el sistema AuditaPro.\n\n"
        "👤 Socio que realizó la creación:\n"
        f" - Nombre: {creator.first_name} {creator.last_name}\n"
        f" - Correo: {creator.email}\n\n"
        "👥 Usuario creado:\n"
        f" - Nombre: {new_user.first_name} {new_user.last_name}\n"
        f" - Correo: {new_user.email}\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [NOTIFY_EMAIL],
        fail_silently=False,
    )
    return True


# 🔹 Reexportamos la función de autoregistro definida en otro archivo
from .autoregistro_email import send_autoregistro_email
