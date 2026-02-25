from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.urls import reverse
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger("email_autoregistro")

# URLs Drive — actualízalas con los enlaces reales
GUIDE_URL = "https://drive.google.com/file/d/1bROWJIfRgMdZHNMopsnkMGvN_g8s8_CD/view"
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1uZj1A00koYzBIz_WcsdGlFFK5a9T8HCi/edit?usp=sharing&ouid=104027925243269597712&rtpof=true&sd=true"
VIDEO_URL = "https://drive.google.com/file/d/106fD9D6sVN1IwZTFlNfZdkZ5aUdfWr21/view"
REVISORIA_GUIDE = "https://drive.google.com/file/d/1ExzqPbiZR52Q-10N50lz35N5RvanH3lm/view?usp=drive_link"


def send_autoregistro_email(invitacion, request):
    path = reverse("autoregistro_registro", kwargs={"token": invitacion.token})
    url_registro = request.build_absolute_uri(path)

    subject = "Invitación para crear tu usuario en AuditaPro"

    context = {
    "url_registro": url_registro,
    "socio": invitacion.socio,
    "email_destino": invitacion.email,

    # 👇 enlaces Drive
    "guide_url": GUIDE_URL,
    #"excel_url": EXCEL_URL,
    "video_url": VIDEO_URL,
    "revisoria_guide": REVISORIA_GUIDE,
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
