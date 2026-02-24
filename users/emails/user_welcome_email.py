from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import strip_tags
from django.conf import settings
import logging, smtplib

logger = logging.getLogger("email_light_final")

# URLs Drive — actualízalas con los enlaces reales
GUIDE_URL = "https://drive.google.com/file/d/1bROWJIfRgMdZHNMopsnkMGvN_g8s8_CD/view"
EXCEL_URL = "https://docs.google.com/spreadsheets/d/1uZj1A00koYzBIz_WcsdGlFFK5a9T8HCi/edit?usp=sharing&ouid=104027925243269597712&rtpof=true&sd=true"
VIDEO_URL = "https://drive.google.com/file/d/106fD9D6sVN1IwZTFlNfZdkZ5aUdfWr21/view"
REVISORIA_GUIDE = "https://drive.google.com/file/d/1ExzqPbiZR52Q-10N50lz35N5RvanH3lm/view?usp=drive_link"


def send_activation_email_light(user, password):
    """
    Correo de bienvenida optimizado (sin adjuntos, con links Drive).
    Limpio, rápido y compatible con Gmail.
    """
    subject = "Acceso al Sistema AuditaPro"
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f9fafb; color:#333; padding:20px;">
      <div style="max-width:600px; margin:auto; background:#fff; border-radius:8px; padding:30px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <h2 style="text-align:center; color:#0056b3;">Bienvenido a AuditaPro</h2>
        <p>Hola <b>{user.first_name}</b>,</p>
        <p>Tu cuenta ha sido creada correctamente. Aquí tienes tus datos de acceso:</p>

        <div style="background:#f3f6fa; padding:15px; border-radius:6px; margin:15px 0;">
          <p><b>Usuario:</b> {user.email}</p>
          <p><b>Contraseña temporal:</b> {password}</p>
        </div>

        <p>Puedes iniciar sesión en el sistema y cambiar tu contraseña al ingresar.</p>

        <h4 style="margin-top:25px; color:#0056b3;">Recursos importantes:</h4>
        <ul style="line-height:1.8;">
          <li>📘 <a href="{GUIDE_URL}" target="_blank">Guía de uso del sistema Audita</a></li>
          <li>🎥 <a href="{VIDEO_URL}" target="_blank">Video de introducción al sistema</a></li>
          <li>🎥 <a href="{REVISORIA_GUIDE}" target="_blank">Video de introducción al sistema</a></li>
        </ul>

        <p>Si necesitas soporte, puedes escribirnos a <a href="mailto:sistemaaudita@gmail.com">sistemaaudita@gmail.com</a>.</p>

        <p style="font-size:12px; color:#666; text-align:center; margin-top:30px;">
          — Equipo AuditaPro<br>
          <i>Correo enviado automáticamente – no responder</i>
        </p>
      </div>
    </body>
    </html>
    """
    text_body = strip_tags(html_body)

    try:
        connection = get_connection(
            host=settings.EMAIL_HOST,
            port=settings.EMAIL_PORT,
            username=settings.EMAIL_HOST_USER,
            password=settings.EMAIL_HOST_PASSWORD,
            use_tls=settings.EMAIL_USE_TLS,
            timeout=15,
        )
        connection.open()
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            to=[user.email],
            connection=connection,
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        connection.close()
        logger.info(f"Correo liviano enviado correctamente a {user.email}")
        return True
    except smtplib.SMTPException as e:
        logger.error(f"Error SMTP: {e}")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
    return False
