from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger("email_autoregistro")


def send_autoregistro_email(invitacion, request):
    path = reverse("autoregistro_registro", kwargs={"token": invitacion.token})
    url_registro = request.build_absolute_uri(path)

    subject = "Invitación para crear tu usuario en AuditaPro"

    context = {
        "url_registro": url_registro,
        "socio": invitacion.socio,      # o invitacion.creado_por si así se llama
        "email_destino": invitacion.email,
    }

    # ⬅️ AQUÍ EL CAMBIO
    html_body = render_to_string("users/autoregistro_email.html", context)

    from_email = getattr(
        settings,
        "AUDITA_NOTIFICATIONS_EMAIL",
        getattr(settings, "DEFAULT_FROM_EMAIL", "sistemaaudita@gmail.com"),
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=html_body,      # si quieres puedes usar strip_tags(html_body)
        from_email=from_email,
        to=[invitacion.email],
    )
    email.attach_alternative(html_body, "text/html")
    email.send()



def send_autoregistro_admin_notification(invitacion):
    """
    Notifica al correo del sistema (dueño) que un socio envió
    un enlace de autoregistro y a qué correo lo envió.
    """
    notify_email = getattr(settings, "AUDITA_NOTIFICATIONS_EMAIL", "sistemaaudita@gmail.com")
    subject = "Autoregistro enviado por un socio"

    socio = invitacion.socio
    body = (
        "Se envió un correo de autoregistro desde AuditaPro.\n\n"
        "👤 Socio que envió el enlace:\n"
        f" - Nombre: {getattr(socio, 'first_name', '')} {getattr(socio, 'last_name', '')}\n"
        f" - Correo: {getattr(socio, 'email', '')}\n\n"
        "📩 Correo destino (cliente):\n"
        f" - {invitacion.email}\n"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [notify_email],
        fail_silently=False,
    )
    return True

def send_autoregistro_success_admin_notification(invitacion, new_user):
    """
    Notifica al correo del sistema (dueño) que el autoregistro fue exitoso
    y se creó el usuario.
    """
    notify_email = getattr(settings, "AUDITA_NOTIFICATIONS_EMAIL", "sistemaaudita@gmail.com")
    subject = "✅ Autoregistro completado: usuario creado"

    socio = invitacion.socio
    socio_nombre = f"{getattr(socio, 'first_name', '')} {getattr(socio, 'last_name', '')}".strip()
    socio_email = getattr(socio, "email", "")

    body = (
        "Se completó exitosamente un autoregistro en AuditaPro.\n\n"
        "👤 Socio que envió el enlace:\n"
        f" - Nombre: {socio_nombre or 'N/A'}\n"
        f" - Correo: {socio_email or 'N/A'}\n\n"
        "📩 Correo destino (cliente invitado):\n"
        f" - {invitacion.email}\n\n"
        "✅ Usuario creado:\n"
        f" - ID: {new_user.id}\n"
        f" - Username: {getattr(new_user, 'username', '')}\n"
        f" - Email: {getattr(new_user, 'email', '')}\n"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [notify_email],
        fail_silently=False,
    )
    return True
