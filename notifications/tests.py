from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from audits.models import Audit
from users.models import Roles

from .models import Notification, NotificationStatus


User = get_user_model()


@override_settings(
    STATICFILES_STORAGE=(
        "django.contrib.staticfiles.storage."
        "StaticFilesStorage"
    ),
    STORAGES={
        "default": {
            "BACKEND": (
                "django.core.files.storage."
                "FileSystemStorage"
            ),
        },
        "staticfiles": {
            "BACKEND": (
                "django.contrib.staticfiles.storage."
                "StaticFilesStorage"
            ),
        },
    },
)
class NotificationTestCase(TestCase):
    def setUp(self):
        self.manager_role = Roles.objects.create(
            name="audit_manager",
            verbose_name="Jefe de Auditoría",
        )
        self.auditor_role = Roles.objects.create(
            name="auditor",
            verbose_name="Auditor",
        )

        self.manager = User.objects.create_user(
            username="manager",
            password="test-password",
            first_name="Jefe",
            last_name="Auditoría",
            email="manager@example.com",
            role=self.manager_role,
            modalidad="G",
        )
        self.auditor = User.objects.create_user(
            username="auditor",
            password="test-password",
            first_name="Ana",
            last_name="Auditora",
            email="auditor@example.com",
            role=self.auditor_role,
            administrador=self.manager,
            modalidad="G",
        )
        self.other_auditor = User.objects.create_user(
            username="other-auditor",
            password="test-password",
            first_name="Otro",
            last_name="Auditor",
            email="other@example.com",
            role=self.auditor_role,
            administrador=self.manager,
            modalidad="G",
        )

        self.audit = Audit.objects.create(
            title="Auditoría de Compras",
            identidad="Empresa de Prueba",
            audit_manager=self.manager,
        )
        self.audit.assigned_users.add(
            self.auditor,
        )

        self.notification = Notification.objects.create(
            notifier=self.manager,
            note="Validar los soportes pendientes.",
            audit=self.audit,
        )
        self.status = NotificationStatus.objects.create(
            notification=self.notification,
            user=self.auditor,
        )

    def test_authenticated_user_can_view_notifications(self):
        self.client.force_login(self.auditor)

        response = self.client.get(
            reverse("notifications")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            f'id="notification-card-{self.status.id}"',
        )

    def test_filters_unread_notifications(self):
        self.client.force_login(self.auditor)

        response = self.client.get(
            reverse("notifications"),
            {"filter": "not_readed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["filter"],
            "not_readed",
        )
        self.assertContains(
            response,
            f'id="notification-card-{self.status.id}"',
        )

    def test_filters_read_notifications(self):
        self.status.read_notification()
        self.client.force_login(self.auditor)

        response = self.client.get(
            reverse("notifications"),
            {"filter": "readed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["filter"],
            "readed",
        )
        self.assertContains(
            response,
            f'id="notification-card-{self.status.id}"',
        )

    def test_manager_can_open_prefilled_notification_form(self):
        self.client.force_login(self.manager)

        response = self.client.get(
            reverse("create_notification"),
            {
                "audit_id": self.audit.id,
                "notifieds_ids": self.auditor.id,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["preselected_audit_id"],
            str(self.audit.id),
        )
        self.assertJSONEqual(
            response.context[
                "preselected_notified_ids_json"
            ],
            [str(self.auditor.id)],
        )

    def test_manager_can_send_notification(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            reverse("create_notification"),
            {
                "audit_id": self.audit.id,
                "notifieds_ids": [self.auditor.id],
                "notification_note": "Revisar el hallazgo 1.",
            },
        )

        self.assertRedirects(
            response,
            reverse("create_notification"),
        )
        self.assertTrue(
            NotificationStatus.objects.filter(
                user=self.auditor,
                notification__audit=self.audit,
                notification__note=(
                    "Revisar el hallazgo 1."
                ),
            ).exists()
        )

    def test_recipient_can_mark_notification_as_read(self):
        self.client.force_login(self.auditor)

        response = self.client.post(
            reverse(
                "mark_notification_as_read",
                kwargs={
                    "notification_status_id": (
                        self.status.id
                    ),
                },
            )
        )

        self.assertRedirects(
            response,
            reverse("notifications"),
        )
        self.status.refresh_from_db()
        self.assertTrue(self.status.is_read)
        self.assertIsNotNone(self.status.readed_date)

    def test_other_user_cannot_mark_notification_as_read(self):
        self.client.force_login(self.other_auditor)

        response = self.client.post(
            reverse(
                "mark_notification_as_read",
                kwargs={
                    "notification_status_id": (
                        self.status.id
                    ),
                },
            )
        )

        self.assertRedirects(
            response,
            reverse("notifications"),
        )
        self.status.refresh_from_db()
        self.assertFalse(self.status.is_read)

        response_messages = list(
            get_messages(
                response.wsgi_request
            )
        )
        self.assertTrue(
            any(
                str(message)
                == (
                    "Usted no está autorizado "
                    "para realizar esta acción."
                )
                for message in response_messages
            )
        )
