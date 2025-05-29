from django.test import TestCase, Client
from .models import Audit
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages

User = get_user_model()


class AuditTestCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
        self.auditor = User.objects.create_user(
            username="auditor",
            first_name="auditor",
            last_name="auditor",
            email="auditor@gmail.com",
            password="password123",
        )

        self.auditor_manager = User.objects.create_user(
            username="auditor_manager",
            first_name="auditor_manager",
            last_name="auditor_manager",
            email="auditor_manager@gmail.com",
            role="audit_manager",
            password="password123",
        )

        self.audit = Audit.objects.create(
            title="Título ejemplo Auditoría 1",
            description="Descripsión ejemplo de Auditoría 1",
            company="Compañía ejemplo Auditoria 1",
            audit_manager=self.auditor_manager,
        )

        self.audit.assigned_users.add(self.auditor)

    def test_audit_can_assign_audit_manager(self):
        auditor_manager1 = User.objects.create(
            username="auditor_manager1",
            first_name="auditor_manager1",
            last_name="auditor_manager1",
            email="auditor_manager1@gmail.com",
            role="audit_manager",
        )

        self.audit.audit_manager = auditor_manager1
        self.audit.save()

    def test_audit_can_assign_users(self):
        auditor1 = User.objects.create(
            username="auditor1",
            first_name="auditor1",
            last_name="auditor1",
            email="auditor1@gmail.com",
        )
        auditor2 = User.objects.create(
            username="auditor2",
            first_name="auditor2",
            last_name="auditor2",
            email="auditor2@gmail.com",
        )
        auditor3 = User.objects.create(
            username="auditor3",
            first_name="auditor3",
            last_name="auditor3",
            email="auditor3@gmail.com",
        )
        supervisor1 = User.objects.create(
            username="supervisor1",
            first_name="supervisor1",
            last_name="supervisor1",
            email="supervisor1@gmail.com",
            role="supervisor",
        )
        supervisor2 = User.objects.create(
            username="supervisor2",
            first_name="supervisor2",
            last_name="supervisor2",
            email="supervisor2@gmail.com",
            role="supervisor",
        )

        self.audit.assigned_users.add(
            auditor1,
            auditor2,
            auditor3,
            supervisor1,
            supervisor2,
        )
        self.audit.save()

    def test_audit_can_unassign_users(self):
        self.audit.assigned_users.remove(self.auditor)
        self.audit.save()

    def test_audit_can_update_data(self):
        new_title = "New title"
        new_description = "New Description"
        new_company = "New Company"
        self.audit.title = new_title
        self.audit.description = new_description
        self.audit.company = new_company
        self.audit.save()

    def test_authenticated_auditor_with_no_assigned_audits(self):
        auditor_without_audits = User.objects.create_user(
            username="auditor_without_audits",
            first_name="auditor_without_audits",
            last_name="auditor_without_audits",
            email="auditor_without_audits@gmail.com",
            password="password123",
        )
        self.client.login(
            email="auditor_without_audits@gmail.com", password="password123"
        )
        response = self.client.get(reverse("assigned_audits"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tiene auditorias asignadas por el momento.")
        card_id = f'id="audit-card-{self.audit.id}"'
        self.assertNotContains(response, card_id)

    def test_authenticated_auditor_with_assigned_audits(self):
        self.client.login(email="auditor@gmail.com", password="password123")
        response = self.client.get(reverse("assigned_audits"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(
            response, "No tiene auditorias asignadas por el momento."
        )
        self.assertContains(response, "Auditorias Asignadas")
        card_id = f'id="audit-card-{self.audit.id}"'
        self.assertContains(response, card_id)

    def test_authenticated_audit_manager_with_no_assigned_audits(self):
        auditor_manager_without_audits = User.objects.create_user(
            username="audit_manager_without_audits",
            first_name="audit_manager_without_audits",
            last_name="audit_manager_without_audits",
            email="audit_manager_without_audits@gmail.com",
            password="password123",
            role="audit_manager",
        )
        self.client.login(
            email="audit_manager_without_audits@gmail.com", password="password123"
        )
        response = self.client.get(reverse("assigned_audits"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear Auditoria")
        self.assertContains(
            response, "No tiene auditorias para gestionar por el momento."
        )
        card_id = f'id="audit-card-{self.audit.id}"'
        self.assertNotContains(response, card_id)

    def test_authenticated_audit_manager_with_assigned_audits(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")
        response = self.client.get(reverse("assigned_audits"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Crear Auditoria")
        self.assertNotContains(
            response, "No tiene auditorias para gestionar por el momento."
        )
        self.assertContains(response, "Auditorias Para Gestionar")
        card_id = f'id="audit-card-{self.audit.id}"'
        self.assertContains(response, card_id)

    def test_authenticated_audit_manager_can_access_create_audit_view(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")
        response = self.client.get(reverse("create_audit"))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_audit_manager_can_create_audit(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")
        response = self.client.get(reverse("create_audit"))
        self.assertEqual(response.status_code, 200)
        form_data = {
            "audit_title": "Nueva Auditoría",
            "audit_description": "Descripción de la nueva auditoría",
            "audit_company": "Nueva Compañía",
            "audit_assigned_users_ids": [
                user.id for user in self.audit.assigned_users.all()
            ],
        }

        response = self.client.post(reverse("create_audit"), data=form_data)

        self.assertEqual(response.status_code, 302)

        self.assertTrue(Audit.objects.filter(title="Nueva Auditoría").exists())

    def test_authenticated_audit_manager_can_manage_audit(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")

        get_url = reverse(
            "manage_audit",
            kwargs={"audit_id": self.audit.id},
        )
        response = self.client.get(get_url)
        self.assertEqual(response.status_code, 200)

        form_data = {
            "audit_title": "Nuevo título modificado",
            "audit_description": "Nueva descripción modificada",
            "audit_company": "Nueva compañía modificada",
        }
        url = reverse("manage_audit", kwargs={"audit_id": self.audit.id})
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse(
            "manage_audit", kwargs={"audit_id": self.audit.id}
        )

        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Auditoria modificada exitosamente."
                for message in messages
            )
        )
        self.assertTrue(Audit.objects.filter(title="Nuevo título modificado").exists())

    def test_authenticated_audit_manager_can_assign_users_to_audit(self):
        self.client.force_login(self.auditor_manager)
        user_to_assign = User.objects.create(
            username="user_to_assign",
            first_name="user_to_assign",
            last_name="user_to_assign",
            email="user_to_assign@gmail.com",
        )
        url = reverse(
            "assign_audit",
            kwargs={"audit_id": self.audit.id, "user_id": user_to_assign.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse(
            "manage_audit", kwargs={"audit_id": self.audit.id}
        )

        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La Auditoría fue asignada a el usuario seleccionado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(self.audit.assigned_users.filter(id=user_to_assign.id).exists())

    def test_authenticated_audit_manager_can_unassign_users_to_audit(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")

        url = reverse(
            "unassign_audit",
            kwargs={"audit_id": self.audit.id, "user_id": self.auditor.id},
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)

        expected_redirect_url = reverse(
            "manage_audit", kwargs={"audit_id": self.audit.id}
        )
        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La Auditoría fue removida del usuario exitosamente."
                for message in messages
            )
        )

        self.assertFalse(self.audit.assigned_users.filter(id=self.auditor.id).exists())

    def test_authenticated_audit_manager_can_assign_multiple_users_to_audit(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")

        user_to_assign_1 = User.objects.create(
            username="user_to_assign_1",
            first_name="user_to_assign_1",
            last_name="user_to_assign_1",
            email="user_to_assign_1@gmail.com",
        )
        user_to_assign_2 = User.objects.create(
            username="user_to_assign_2",
            first_name="user_to_assign_2",
            last_name="user_to_assign_2",
            email="user_to_assign_2@gmail.com",
        )
        user_to_assign_3 = User.objects.create(
            username="user_to_assign_3",
            first_name="user_to_assign_3",
            last_name="user_to_assign_3",
            email="user_to_assign_3@gmail.com",
        )
        user_to_assign_4 = User.objects.create(
            username="user_to_assign_4",
            first_name="user_to_assign_4",
            last_name="user_to_assign_4",
            email="user_to_assign_4@gmail.com",
        )
        form_data = {
            "user_ids": [
                user_to_assign_1.id,
                user_to_assign_2.id,
                user_to_assign_3.id,
                user_to_assign_4.id,
            ]
        }

        url = reverse(
            "manage_audit_assign_audit",
            kwargs={"audit_id": self.audit.id},
        )
        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse(
            "manage_audit", kwargs={"audit_id": self.audit.id}
        )

        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La Auditoría fue asignada a los usuarios seleccionados con éxito."
                for message in messages
            )
        )
        self.assertTrue(
            (
                self.audit.assigned_users.filter(id=user_to_assign_1.id).exists(),
                self.audit.assigned_users.filter(id=user_to_assign_2.id).exists(),
                self.audit.assigned_users.filter(id=user_to_assign_3.id).exists(),
                self.audit.assigned_users.filter(id=user_to_assign_4.id).exists(),
            )
        )

    def test_authenticated_audit_manager_can_delete_audit(self):
        self.client.login(email="auditor_manager@gmail.com", password="password123")

        audit_to_delete = Audit.objects.create(
            title="Auditoría para borrar",
            description="Descripsión ejemplo de Auditoría para borrar",
            company="Compañía ejemplo Auditoria para borrar",
            audit_manager=self.auditor_manager,
        )
        url = reverse(
            "delete_audit",
            kwargs={"audit_id": audit_to_delete.id},
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La Auditoría fue borrada exitosamente."
                for message in messages
            )
        )
        self.assertFalse(Audit.objects.filter(id=audit_to_delete.id).exists())

    def test_audit_can_be_deleted(self):
        self.audit.delete()
