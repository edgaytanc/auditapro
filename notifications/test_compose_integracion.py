"""Pruebas de compatibilidad de Crear Notificación. No alteran datos de producción."""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from audits.models import Audit
from users.models import Roles
from notifications.models import Notification, NotificationStatus


User = get_user_model()


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage",
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class NotificacionesComposeIntegracionTests(TestCase):
    def setUp(self):
        jefe_rol = Roles.objects.create(name="audit_manager", verbose_name="Jefe de Auditoría")
        auditor_rol = Roles.objects.create(name="auditor", verbose_name="Auditor")
        self.jefe = User.objects.create_user(
            username="compose-jefe", password="test-password", email="jefe@gmail.com",
            first_name="Jefe", role=jefe_rol, modalidad="G",
        )
        self.auditor = User.objects.create_user(
            username="compose-auditor", password="test-password", email="auditor@example.com",
            first_name="Ana", role=auditor_rol, administrador=self.jefe, modalidad="G",
        )
        self.ajeno = User.objects.create_user(
            username="compose-ajeno", password="test-password", email="ajeno@example.com",
            first_name="Otro", role=auditor_rol, administrador=self.jefe, modalidad="G",
        )
        self.audit = Audit.objects.create(
            title="Prueba de notificación", audit_manager=self.jefe,
        )
        self.audit.assigned_users.add(self.auditor)

    def test_formulario_conserva_instructivo_botones_y_scripts_nuevos(self):
        self.client.force_login(self.jefe)
        response = self.client.get(reverse("create_notification"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for marker in (
            "Cómo funciona", "Envío externo", 'id="btnGmail"',
            'id="btnOutlookWeb"', 'id="btnMailto"', 'id="correoAviso"',
            "AUDITA_COMPOSE_NOTIFICATIONS_VERSION", "--notif-blue",
            "Guardar notificación",
        ):
            self.assertIn(marker, html)
        self.assertNotIn('<script src="/static/js/notifications-compose-v2.js', html)
        audits = json.loads(response.context["audits_json"])
        users = json.loads(response.context["notifieds_json"])
        self.assertIn(str(self.auditor.id), [str(user["id"]) for user in users])
        self.assertEqual(len(audits), 1)

    def test_guardado_interno_sigue_creando_notificacion_y_estado(self):
        self.client.force_login(self.jefe)
        response = self.client.post(reverse("create_notification"), {
            "audit_id": self.audit.id,
            "notifieds_ids": [self.auditor.id],
            "notification_note": "Revisar documentos de la auditoría.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.count(), 1)
        status = NotificationStatus.objects.get()
        self.assertEqual(status.user_id, self.auditor.id)
        self.assertEqual(status.notification.audit_id, self.audit.id)

    def test_destinatarios_ajenos_rechazados_por_backend(self):
        self.client.force_login(self.jefe)
        response = self.client.post(reverse("create_notification"), {
            "audit_id": self.audit.id,
            "notifieds_ids": [self.ajeno.id],
            "notification_note": "No debe enviarse.",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(NotificationStatus.objects.exists())

    def test_auditor_recibe_como_destinatario_solamente_al_jefe(self):
        self.client.force_login(self.auditor)
        response = self.client.get(reverse("create_notification"))
        self.assertEqual(response.status_code, 200)
        users = json.loads(response.context["notifieds_json"])
        self.assertEqual([user["id"] for user in users], [self.jefe.id])
