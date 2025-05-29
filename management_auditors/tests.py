from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from audits.models import Audit

User = get_user_model()


class ManagementAuditosTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.audit_manager = User.objects.create_user(
            email="audit_manager",
            username="audit_manager",
            first_name="audit_manager",
            last_name="audit_manager",
            password="123",
            role="audit_manager",
        )

        self.auditor_to_manage = User.objects.create_user(
            username="auditor_to_manage",
            email="auditor_to_manage",
            first_name="auditor_to_manage",
            last_name="auditor_to_manage",
            password="123",
        )

    def test_audit_manager_can_access_manage_auditors_page(self):
        self.client.force_login(self.audit_manager)

        response = self.client.get(reverse("manage_auditors"))

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Gestionar Auditores")

    def test_user_not_audit_manager_can_not_access_to_manage_auditors_page(self):
        user_not_audit_manager = User.objects.create_user(
            username="user_not_audit_manager",
            email="user_not_audit_manager",
            first_name="user_not_audit_manager",
            last_name="user_not_audit_manager",
            password="123",
        )

        self.client.force_login(user_not_audit_manager)

        response = self.client.get(reverse("manage_auditors"))

        self.assertEqual(response.status_code, 302)

        expected_url = reverse("user")

        self.assertRedirects(response, expected_url)

    def test_audit_manager_can_access_manage_auditor_page(self):

        self.client.force_login(self.audit_manager)

        response = self.client.get(
            reverse("manage_auditor", kwargs={"user_id": self.auditor_to_manage.id})
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Gestionar Auditor")
        self.assertContains(response, self.auditor_to_manage.get_full_name())

    def test_audit_manager_can_assign_audit_to_auditor(self):
        self.client.force_login(self.audit_manager)
        form_data = {
            "audits_ids": [
                audit.id
                for audit in [
                    Audit.objects.create(
                        title=f"Audit {i+1}",
                        description=f"Description {i+1}",
                        audit_manager=self.audit_manager,
                    )
                    for i in range(3)
                ]
            ]
        }

        response = self.client.post(
            reverse("assign_audit", kwargs={"user_id": self.auditor_to_manage.id}),
            data=form_data,
        )

        self.assertEqual(response.status_code, 302)
        expected_url = reverse(
            "manage_auditor", kwargs={"user_id": self.auditor_to_manage.id}
        )
        self.assertRedirects(response, expected_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Se le han asignado las auditorías correctamente al usuario seleccionado."
                for message in messages
            )
        )

    def test_audit_manager_user_do_not_exits_error_assign_audit(self):
        self.client.force_login(self.audit_manager)
        form_data = {
            "audits_ids": [
                audit.id
                for audit in [
                    Audit.objects.create(
                        title=f"Audit {i+1}",
                        description=f"Description {i+1}",
                        audit_manager=self.audit_manager,
                    )
                    for i in range(3)
                ]
            ]
        }
        response = self.client.post(
            reverse("assign_audit", kwargs={"user_id": "3000"}), data=form_data
        )

        self.assertEqual(response.status_code, 302)

    def test_audit_manager_is_unathorized_to_assign_audit_to_user(self):
        audit_manager_unathorized = User.objects.create_user(
            username="audit_manager_unathorized",
            email="audit_manager_unathorized",
            first_name="audit_manager_unathorized",
            last_name="audit_manager_unathorized",
            password="123",
            role="audit_manager",
        )

        form_data = {
            "audits_ids": [
                audit.id
                for audit in [
                    Audit.objects.create(
                        title=f"Audit {i+1}",
                        description=f"Description {i+1}",
                        audit_manager=self.audit_manager,
                    )
                    for i in range(3)
                ]
            ]
        }

        self.client.force_login(audit_manager_unathorized)

        response = self.client.post(
            reverse("assign_audit", kwargs={"user_id": self.auditor_to_manage.id}),
            data=form_data,
        )

        self.assertEqual(response.status_code, 302)
        expected_url = reverse(
            "manage_auditor", kwargs={"user_id": self.auditor_to_manage.id}
        )
        self.assertRedirects(response, expected_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "El jefe de auditoría para esta auditoría no es el que está registrado."
                for message in messages
            )
        )
