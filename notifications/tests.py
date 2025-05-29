from django.test import TestCase, Client
from .models import Notification, NotificationStatus
from django.contrib.auth import get_user_model
from audits.models import Audit
from django.urls import reverse
from urllib.parse import urlencode
from django.contrib.messages import get_messages

User = get_user_model()


class NotificationTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.notifier = User.objects.create(
            username="notifier",
            first_name="notifier",
            last_name="notifier",
            email="notifier@gmail.com",
            role="audit_manager",
        )

        audit_manager = User.objects.create_user(
            username="audit_manager",
            first_name="audit_manager",
            last_name="audit_manager",
            email="audit_manager@gmail.com",
            role="audit_manager",
        )
        self.notification_note = "Notification note example"

        self.notification_audit = Audit.objects.create(
            title="Audit", description="description", audit_manager=audit_manager
        )
        self.notification_audit.assigned_users.add(self.notifier)

        self.notification = Notification.objects.create(
            notifier=self.notifier,
            note=self.notification_note,
            audit=self.notification_audit,
        )

        self.notified = User.objects.create_user(
            username="notified",
            first_name="notified",
            last_name="notified",
            email="notified@gmail.com",
            role="supervisor",
            password="123",
        )
        self.notification_audit.assigned_users.add(self.notified)

        self.notification_status = NotificationStatus.objects.create(
            notification=self.notification, user=self.notified
        )

        self.notification_audit.save()

        self.notification.save()
        self.notification_status.save()
        self.notified_with_readed_notification = User.objects.create_user(
            username="notified_with_readed_notification",
            first_name="notified_with_readed_notification",
            last_name="notified_with_readed_notification",
            email="notified_with_readed_notification@gmail.com",
            role="supervisor",
            password="123",
        )

        self.notification_audit.assigned_users.add(
            self.notified_with_readed_notification
        )
        self.notification_status_readed = NotificationStatus.objects.create(
            notification=self.notification, user=self.notified_with_readed_notification
        )

        self.notification_status_readed.read_notification()
        self.notification_status_readed.save()

    def test_user_authenticated_can_access_to_notifications_page_with_notifications(
        self,
    ):
        self.client.force_login(self.notified)

        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notificaciones")
        card_id = f'id="notification-card-{self.notification_status.id}"'
        self.assertContains(response, card_id)

    def test_user_authenticated_can_access_to_notifications_page_without_notifications(
        self,
    ):
        user_without_notifications = User.objects.create_user(
            username="user_without_notifications",
            email="user_without_notifications@gmail.com",
            password="123",
            first_name="User",
            last_name="User",
        )
        self.client.force_login(user_without_notifications)

        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tiene notificaciones pendientes.")
        card_id = f'id="notification-card-{self.notification_status.id}"'
        self.assertNotContains(response, card_id)

    def test_user_authenticated_can_view_readed_filter_notifications(self):
        self.client.force_login(self.notified_with_readed_notification)

        url = reverse("notifications")

        query_params = urlencode({"filter": "readed"})

        full_url = f"{url}?{query_params}"

        response = self.client.get(full_url)
        self.assertEqual(response.status_code, 200)
        card_id = f'id="notification-card-{self.notification_status_readed.id}"'
        self.assertContains(response, card_id)
        self.assertNotContains(response, "Marcar como Leída")

    def test_user_authenticated_can_view_not_readed_filter_notifications(self):
        user_with_not_readed_notifications = User.objects.create_user(
            username="user_with_readed_notifications",
            email="user_with_readed_notifications@gmail.com",
            first_name="user_with_readed_notifications",
            last_name="user_with_readed_notifications",
            password="123",
        )

        self.notification_audit.assigned_users.add(user_with_not_readed_notifications)

        self.client.force_login(user_with_not_readed_notifications)

        notificion_to_read = Notification.objects.create(
            notifier=self.notifier,
            note=self.notification_note,
            audit=self.notification_audit,
        )

        notification_status = NotificationStatus.objects.create(
            user=user_with_not_readed_notifications, notification=notificion_to_read
        )

        url = reverse("notifications")

        query_params = urlencode({"filter": "not_readed"})

        full_url = f"{url}?{query_params}"

        response = self.client.get(full_url)
        self.assertEqual(response.status_code, 200)
        card_id = f'id="notification-card-{notification_status.id}"'
        self.assertContains(response, card_id)
        self.assertContains(response, "Marcar como Leída")

    def test_user_authenticated_can_read_notification(self):
        self.client.force_login(self.notified)

        response = self.client.get(reverse("notifications"))

        self.assertEqual(response.status_code, 200)
        post_response = self.client.post(
            reverse(
                "mark_notification_as_read",
                kwargs={"notification_status_id": self.notification_status.id},
            )
        )

        self.assertEqual(post_response.status_code, 302)
        expected_redirect_url = reverse("notifications")
        self.assertRedirects(post_response, expected_redirect_url)

    def test_user_authenticated_invalid_user_to_notification_status(self):
        user_unathorized = User.objects.create_user(
            username="user_unathorized",
            email="user_unathorized@gmail.com",
            first_name="user_unathorized",
            last_name="user_unathorized",
            password="123",
        )

        self.client.force_login(user_unathorized)

        response = self.client.get(reverse("notifications"))

        self.assertEqual(response.status_code, 200)

        post_response = self.client.post(
            reverse(
                "mark_notification_as_read",
                kwargs={"notification_status_id": self.notification_status.id},
            )
        )

        self.assertEqual(post_response.status_code, 302)
        expected_redirect_url = reverse("notifications")

        self.assertRedirects(post_response, expected_redirect_url)

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Usted no está autorizado para realizar esta acción."
                for message in messages
            )
        )

    def test_user_authenticaed_invalid_notification_status_id(self):
        self.client.force_login(self.notified)

        response = self.client.get(reverse("notifications"))

        self.assertEqual(response.status_code, 200)

        post_response = self.client.post(
            reverse(
                "mark_notification_as_read",
                kwargs={"notification_status_id": 300},
            )
        )

        self.assertEqual(post_response.status_code, 302)
        expected_redirect_url = reverse("notifications")

        self.assertRedirects(post_response, expected_redirect_url)

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La notificación ingresada no existe."
                for message in messages
            )
        )
