from datetime import datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from audits.models import Audit
from users.models import Roles
from .models import (
    AuditMarks,
    AuditTimeSummary,
    Country,
    CurrencyType,
    SummaryHoursWorked,
    WorkingPapersStatus,
    CurrentStatus,
    Months,
)
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from common.templatetags.filters import format_duration_day_number
from django.utils import timezone

User = get_user_model()


# ESTOS TEST SOLO FUNCIONAN EN LA PRIMERA VERSIÓN QUE MANDÉ, actualmente no funcionan del todo porque se cambiaron las reglas.
"""class AuditTimeSummaryTestCase(TestCase):
    def setUp(self):
        self.auditor_manager = User.objects.create_user(
            username="auditor_manager",
            first_name="auditor_manager",
            last_name="auditor_manager",
            email="auditor_manager@gmail.com",
            role="audit_manager",
            password="password123",
        )

        self.auditor = User.objects.create_user(
            username="auditor",
            first_name="auditor",
            last_name="auditor",
            email="auditor@gmail.com",
            password="password123",
        )

        self.audit = Audit.objects.create(
            title="Título ejemplo Auditoría 1",
            description="Descripsión ejemplo de Auditoría 1",
            company="Compañía ejemplo Auditoria 1",
            audit_manager=self.auditor_manager,
        )

        self.audit.assigned_users.add(self.auditor)

        self.audit_time_summary = AuditTimeSummary.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            appointment_number=12345,
            full_name="Usuario Usuario",
            position="Auditor",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Lorem ipsum dolor...",
        )

    def test_difference_calculation(self):
        self.audit_time_summary.save()
        self.assertEqual(
            self.audit_time_summary.differences, format_duration_field(5, "days")
        )

    def test_audit_time_summary_can_update_data(self):
        new_appointmen_number = 5678
        new_full_name = "New Full Name"
        new_position = "New Position"
        new_scheduled_days = format_duration_field(20, "days")
        new_worked_days = format_duration_field(15, "days")
        new_differences = new_scheduled_days - new_worked_days
        new_observations = "New Observations"
        self.audit_time_summary.appointment_number = new_appointmen_number
        self.audit_time_summary.full_name = new_full_name
        self.audit_time_summary.position = new_position
        self.audit_time_summary.scheduled_days = new_scheduled_days
        self.audit_time_summary.worked_days = new_worked_days
        self.audit_time_summary.differences = new_differences
        self.audit_time_summary.observations = new_observations

        self.assertTrue(
            self.audit_time_summary.appointment_number, new_appointmen_number
        )
        self.assertTrue(self.audit_time_summary.full_name, new_full_name)
        self.assertTrue(self.audit_time_summary.position, new_position)
        self.assertTrue(self.audit_time_summary.scheduled_days, new_scheduled_days)
        self.assertTrue(self.audit_time_summary.worked_days, new_worked_days)
        self.assertTrue(self.audit_time_summary.differences, new_differences)
        self.assertTrue(self.audit_time_summary.observations, new_observations)

    def test_audit_time_summary_can_be_deleted(self):
        audit_time_summary_to_delete = AuditTimeSummary.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            appointment_number=999999,
            full_name="Borrar",
            position="Borrar",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Borrar",
        )

        audit_time_summary_to_delete.delete()

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                appointment_number=999999,
                full_name="Borrar",
                position="Borrar",
                scheduled_days=format_duration_field(10, "days"),
                worked_days=format_duration_field(5, "days"),
                observations="Borrar",
            ).exists()
        )

    def test_user_can_access_to_tools_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "tools",
        )
        response = self.client.get(get_url)
        self.assertContains(response, "Herramientas")
        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_audit_summary_table_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "audit_time_summary_table",
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.audit_time_summary.full_name)
        self.assertContains(response, self.audit_time_summary.observations)
        self.assertContains(response, self.audit_time_summary.appointment_number)
        self.assertContains(response, "Resumen de Tiempo Auditoría")
        self.assertContains(response, "Crear Registro")
        self.assertContains(response, self.audit_time_summary.appointment_number)

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_audit_summary_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "audit_time_summary", kwargs={"id": self.audit_time_summary.pk}
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.audit_time_summary.full_name)
        self.assertContains(response, self.audit_time_summary.observations)
        self.assertContains(response, self.audit_time_summary.appointment_number)
        self.assertContains(
            response, f"Nombramiento No. {self.audit_time_summary.appointment_number}"
        )
        self.assertContains(response, self.audit_time_summary.appointment_number)

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_create_audit_summary_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "create_audit_time_summary",
        )
        response = self.client.get(get_url)

        self.assertContains(response, "Guardar")
        self.assertContains(response, "Observaciones")
        self.assertContains(response, "Días Reales Trabajados")
        self.assertContains(response, "Días Programados")
        self.assertContains(response, "Cargo")
        self.assertContains(response, "Nombre Completo")
        self.assertContains(response, "Número de nombramiento")
        self.assertContains(response, "Número de nombramiento")
        self.assertContains(response, "Crear Resumen")

        self.assertEqual(response.status_code, 200)

    def test_user_can_create_audit_time_summary(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "appointment-number": "1234",
            "observations": "Observaciones ejemplo",
            "worked-days": "20",
            "scheduled-days": "25",
            "position": "Auditor",
            "full-name": "Nombre Completo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("audit_time_summary_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Resumen de tiempo de Auditoría creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            AuditTimeSummary.objects.filter(
                appointment_number=1234,
                observations="Observaciones ejemplo",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                position="Auditor",
                full_name="Nombre Completo",
            ).exists()
        )

    def test_user_create_audit_time_summary_without_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "appointment-number": "1234",
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "25",
            "position": "Invalid",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no puede estar vacía."
                for message in messages
            )
        )
        self.assertFalse(
            AuditTimeSummary.objects.filter(
                appointment_number=1234,
                observations="Invalid",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                position="Invalid",
                full_name="Invalid",
            ).exists()
        )

    def test_user_create_audit_time_summary_invalid_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": "Invalid",
            "appointment-number": "1234",
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "25",
            "position": "Invalid",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no existe."
                for message in messages
            )
        )
        self.assertFalse(
            AuditTimeSummary.objects.filter(
                appointment_number=1234,
                observations="Invalid",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                position="Invalid",
                full_name="Invalid",
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_appointment_number_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "25",
            "position": "Invalid",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "El número de nombramiento completo no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                position="Invalid",
                full_name="Invalid",
            ).exists()
        )

    def test_user_create_audit_time_summary_invalid_appointment_number_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "25",
            "full-name": "Invalid",
            "scheduled-days": "30",
            "position": "Invalid",
            "appointment-number": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "El número de nombramiento no puede contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                scheduled_days=timedelta(days=30),
                position="Invalid",
                worked_days=timedelta(days=25),
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_worked_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "appointment-number": "1234",
            "scheduled-days": "25",
            "position": "Invalid",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Los días trabajados no pueden estar vacíos."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                appointment_number=1234,
                scheduled_days=timedelta(days=25),
                position="Invalid",
                full_name="Invalid",
            ).exists()
        )

    def test_user_create_audit_time_summary_invalid_worked_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "Invalid",
            "scheduled-days": "20",
            "position": "Invalid",
            "appointment-number": "1234",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Los días trabajados ingresados no pueden contener letras, sólo números enteros."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                scheduled_days=timedelta(days=20),
                position="Invalid",
                appointment_number=1234,
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_scheduled_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "20",
            "appointment-number": "1234",
            "position": "Invalid",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Los días programados no pueden estar vacíos."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                appointment_number=1234,
                position="Invalid",
                full_name="Invalid",
            ).exists()
        )

    def test_user_create_audit_time_summary_invalid_scheduled_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "Invalid",
            "position": "Invalid",
            "appointment-number": "1234",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Los días programados ingresados no pueden contener letras, sólo números enteros."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                position="Invalid",
                appointment_number=1234,
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_full_name_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "25",
            "position": "Invalid",
            "appointment-number": "1234",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El nombre completo no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                position="Invalid",
                appointment_number=1234,
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_position_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "25",
            "appointment-number": "1234",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_audit_time_summary")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El cargo no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                scheduled_days=timedelta(days=25),
                appointment_number=1234,
                full_name="Invalid",
            ).exists()
        )

    def test_user_can_create_audit_time_summary_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_audit_time_summary")

        form_data = {
            "audit": self.audit.pk,
            "appointment-number": "56789",
            "worked-days": "35",
            "scheduled-days": "40",
            "position": "Auditor",
            "full-name": "Nombre Completo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("audit_time_summary_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Resumen de tiempo de Auditoría creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            AuditTimeSummary.objects.filter(
                appointment_number=56789,
                worked_days=timedelta(days=35),
                scheduled_days=timedelta(days=40),
                position="Auditor",
                full_name="Nombre Completo",
            ).exists()
        )

    def test_user_can_delete_audit_time_summary(self):
        self.client.login(username="auditor", password="password123")

        audit_time_summary_to_delete = AuditTimeSummary.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            appointment_number=999999,
            full_name="Borrar",
            position="Borrar",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Borrar",
        )

        get_url = reverse(
            "delete_audit_time_summary", kwargs={"id": audit_time_summary_to_delete.pk}
        )

        response = self.client.post(get_url)

        self.assertEqual(response.status_code, 302)

        expected_redirect_url = reverse("audit_time_summary_table")
        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Resumen de tiempo de Auditoría eliminado exitosamente."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(id=audit_time_summary_to_delete.pk).exists()
        )

    def test_user_delete_audit_time_summary_no_exits_id(self):
        self.client.login(username="auditor", password="password123")

        audit_time_summary_to_delete = AuditTimeSummary.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            appointment_number=999999,
            full_name="Borrar",
            position="Borrar",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Borrar",
        )

        post_url = reverse("delete_audit_time_summary", kwargs={"id": 333})

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            AuditTimeSummary.objects.filter(id=audit_time_summary_to_delete.pk).exists()
        )

    def test_user_delete_audit_time_summary_that_not_is_them_own(self):
        self.client.login(username="auditor", password="password123")
        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_delete_working",
            first_name="other_auditor_for_to_delete_working",
            last_name="other_auditor_for_to_delete_working",
            email="other_auditor_for_to_delete_working@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)
        audit_time_summary_to_delete = AuditTimeSummary.objects.create(
            audit=self.audit,
            auditor=other_auditor,
            appointment_number=999999,
            full_name="Borrar",
            position="Borrar",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Borrar",
        )

        post_url = reverse(
            "delete_status_of_work_papers",
            kwargs={"id": audit_time_summary_to_delete.pk},
        )

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            AuditTimeSummary.objects.filter(id=audit_time_summary_to_delete.pk).exists()
        )

    def test_user_can_update_audit_time_summary(self):
        self.client.login(username="auditor", password="password123")
        audit_time_summary_to_update = AuditTimeSummary.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            appointment_number=24558,
            full_name="Usuario Usuario",
            position="Auditor",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Lorem ipsum dolor...",
        )
        post_url = reverse(
            "audit_time_summary", kwargs={"id": audit_time_summary_to_update.pk}
        )
        form_data = {
            "appointment-number": "993939",
            "observations": "Updated Observations",
            "worked-days": "30",
            "scheduled-days": "35",
            "position": "Auditor",
            "full-name": "Updated Full Name",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "993939")
        self.assertContains(response, "Updated Observations")
        self.assertContains(response, "Updated Full Name")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Resumen de tiempo de Auditoría actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            AuditTimeSummary.objects.filter(
                appointment_number=993939,
                observations="Updated Observations",
                worked_days=timedelta(days=30),
                scheduled_days=timedelta(days=35),
                position="Auditor",
                full_name="Updated Full Name",
            ).exists()
        )

    def test_user_update_audit_time_summary_invalid_appointment_number_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "audit_time_summary", kwargs={"id": self.audit_time_summary.pk}
        )

        form_data = {
            "observations": "Invalid",
            "worked-days": "25",
            "full-name": "Invalid",
            "scheduled-days": "30",
            "position": "Invalid",
            "appointment-number": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.audit_time_summary.appointment_number)
        self.assertContains(response, self.audit_time_summary.observations)
        self.assertContains(response, self.audit_time_summary.full_name)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "El número de nombramiento no puede contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                scheduled_days=timedelta(days=30),
                position="Invalid",
                worked_days=timedelta(days=25),
            ).exists()
        )

    def test_user_update_audit_time_summary_invalid_worked_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "audit_time_summary", kwargs={"id": self.audit_time_summary.pk}
        )

        form_data = {
            "observations": "Invalid",
            "worked-days": "Invalid",
            "scheduled-days": "20",
            "position": "Invalid",
            "appointment-number": "1234",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.audit_time_summary.appointment_number)
        self.assertContains(response, self.audit_time_summary.observations)
        self.assertContains(response, self.audit_time_summary.full_name)
        messages = list(get_messages(response.wsgi_request))
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Los días trabajados ingresados no pueden contener letras, sólo números enteros."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                scheduled_days=timedelta(days=20),
                position="Invalid",
                appointment_number=1234,
            ).exists()
        )

    def test_user_update_audit_time_summary_invalid_scheduled_days_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "audit_time_summary", kwargs={"id": self.audit_time_summary.pk}
        )

        form_data = {
            "observations": "Invalid",
            "worked-days": "20",
            "scheduled-days": "Invalid",
            "position": "Invalid",
            "appointment-number": "1234",
            "full-name": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.audit_time_summary.appointment_number)
        self.assertContains(response, self.audit_time_summary.observations)
        self.assertContains(response, self.audit_time_summary.full_name)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Los días programados ingresados no pueden contener letras, sólo números enteros."
                for message in messages
            )
        )

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                observations="Invalid",
                worked_days=timedelta(days=20),
                position="Invalid",
                appointment_number=1234,
            ).exists()
        )

    def test_user_can_update_audit_time_summary_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "audit_time_summary", kwargs={"id": self.audit_time_summary.pk}
        )

        form_data = {
            "appointment-number": "56789",
            "worked-days": "35",
            "scheduled-days": "40",
            "position": "Auditor",
            "full-name": "Nombre Completo",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "56789")
        self.assertContains(response, "35")
        self.assertContains(response, "40")
        self.assertContains(response, "Auditor")
        self.assertContains(response, "Nombre Completo")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Resumen de tiempo de Auditoría actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            AuditTimeSummary.objects.filter(
                appointment_number=56789,
                worked_days=timedelta(days=35),
                scheduled_days=timedelta(days=40),
                position="Auditor",
                full_name="Nombre Completo",
            ).exists()
        )

    def test_user_update_audit_summary_time_that_not_is_them_own(self):
        self.client.login(username="auditor", password="password123")
        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_update_working",
            first_name="other_auditor_for_to_update_working",
            last_name="other_auditor_for_to_update_working",
            email="other_auditor_for_to_update_working@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)

        audit_time_summary_to_update = AuditTimeSummary.objects.create(
            auditor=other_auditor,
            audit=self.audit,
            appointment_number=24558,
            full_name="Usuario Usuario",
            position="Auditor",
            scheduled_days=format_duration_field(10, "days"),
            worked_days=format_duration_field(5, "days"),
            observations="Lorem ipsum dolor...",
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": audit_time_summary_to_update.pk}
        )

        form_data = {
            "appointment-number": "56789",
            "worked-days": "35",
            "scheduled-days": "40",
            "position": "Auditor",
            "full-name": "Nombre Completo",
            "observations": "Hola mundo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 404)

        self.assertFalse(
            AuditTimeSummary.objects.filter(
                appointment_number=56789,
                worked_days=timedelta(days=35),
                scheduled_days=timedelta(days=40),
                position="Auditor",
                full_name="Nombre Completo",
                observations="Hola mundo",
            ).exists()
        )
"""

"""class SummaryHoursWorkedTestCase(TestCase):
    def setUp(self):
        self.month = Months.objects.create(name="Enero")

        self.auditor_manager = User.objects.create_user(
            username="auditor_manager",
            first_name="auditor_manager",
            last_name="auditor_manager",
            email="auditor_manager@gmail.com",
            role="audit_manager",
            password="password123",
        )

        self.auditor = User.objects.create_user(
            username="auditor",
            first_name="auditor",
            last_name="auditor",
            email="auditor@gmail.com",
            password="password123",
        )

        self.audit = Audit.objects.create(
            title="Título ejemplo Auditoría 1",
            description="Descripsión ejemplo de Auditoría 1",
            company="Compañía ejemplo Auditoria 1",
            audit_manager=self.auditor_manager,
        )

        self.audit.assigned_users.add(self.auditor)

        self.summary_hours_worked = SummaryHoursWorked.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            month=self.month,
            total_scheduled_hours=format_duration_field(10, "hours"),
            total_hours_worked=format_duration_field(5, "hours"),
            observations="Lorem ipsum dolor...",
        )

        self.month2 = Months.objects.create(name="marzo")

    def test_difference_calculation(self):
        self.summary_hours_worked.save()
        self.assertEqual(
            self.summary_hours_worked.differences, format_duration_field(5, "hours")
        )

    def test_summary_hours_worked_can_update_data(self):
        new_month = Months.objects.create(name="Febrero")
        new_total_scheduled_hours = format_duration_field(20, "hours")
        new_total_hous_worked = format_duration_field(5, "hours")
        new_observations = "New Observations"

        self.summary_hours_worked.month = new_month
        self.summary_hours_worked.total_scheduled_hours = new_total_scheduled_hours
        self.summary_hours_worked.total_hours_worked = new_total_hous_worked

        self.assertTrue(self.summary_hours_worked.month, new_month)
        self.assertTrue(
            self.summary_hours_worked.total_scheduled_hours, new_total_scheduled_hours
        )
        self.assertTrue(
            self.summary_hours_worked.total_hours_worked, new_total_hous_worked
        )

        self.assertTrue(self.summary_hours_worked.observations, new_observations)

    def test_summary_hours_worked_can_be_deleted(self):
        summary_hours_worked_to_delete = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            month=self.month,
            total_scheduled_hours=format_duration_field(20, "hours"),
            total_hours_worked=format_duration_field(15, "hours"),
            observations="Observaciones",
        )

        summary_hours_worked_to_delete.delete()

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=format_duration_field(20, "hours"),
                total_hours_worked=format_duration_field(15, "hours"),
                observations="Observaciones",
            ).exists()
        )

    def test_user_can_access_to_summary_hours_worked_table(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "summary_worked_hours_table",
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.summary_hours_worked.month)
        self.assertContains(response, self.summary_hours_worked.observations)
        self.assertContains(response, "Crear Registro")
        self.assertContains(response, "10 horas")
        self.assertContains(response, "5 horas")

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_summary_worked_hours_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.summary_hours_worked.month)
        self.assertContains(response, self.summary_hours_worked.observations)
        self.assertContains(
            response, format_duration_day_number(self.summary_hours_worked.differences)
        )
        self.assertContains(
            response,
            format_duration_day_number(self.summary_hours_worked.total_hours_worked),
        )
        self.assertContains(
            response,
            format_duration_day_number(self.summary_hours_worked.total_scheduled_hours),
        )

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_create_summary_worked_hours_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "create_summary_hours_worked",
        )
        response = self.client.get(get_url)

        self.assertContains(response, "Guardar")
        self.assertContains(response, "Mes")
        self.assertContains(response, "Total de horas trabajadas")
        self.assertContains(response, "Total de horas programadas")
        self.assertContains(response, "Observaciones")
        self.assertContains(response, "Guardar")

        self.assertEqual(response.status_code, 200)

    def test_user_can_create_summary_hours_worked(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "month": self.month.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Observaciones Ejemplo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("summary_worked_hours_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Resumen de Horas Trabajadas creado exitosamente."
                for message in messages
            )
        )
        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                observations="Observaciones Ejemplo",
            ).exists()
        )

    def test_user_create_summary_hours_worked_without_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "month": self.month.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no puede estar vacía."
                for message in messages
            )
        )
        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                observations="Invalid",
            ).exists()
        )

    def test_user_create_summary_hours_worked_invalid_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": "Invalid",
            "month": self.month.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no existe."
                for message in messages
            )
        )
        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                observations="Invalid",
            ).exists()
        )

    def test_user_create_summary_hours_worked_whithout_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                observations="Invalid",
            ).exists()
        )

    def test_user_create_summary_hours_worked_invalid_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
            "month": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
            ).exists()
        )

    def test_user_create_summary_hours_worked_does_not_exits_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
            "month": 3333333,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado no existe o es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                audit=self.audit,
            ).exists()
        )

    def test_user_create_summary_hours_worked_whithout_scheduled_hours_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "month": self.month.pk,
            "worked-hours": "25",
            "observations": "Observaciones Ejemplo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas prrogramadas ingresadas no pueden estar vacías."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                total_hours_worked=timedelta(hours=25),
                observations="Invalid",
                month=self.month,
            ).exists()
        )

    def test_user_create_summary_hours_worked_invalid_scheduled_hours_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "Invalid",
            "worked-hours": "25",
            "observations": "Invalid",
            "month": self.month.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas programadas no pueden contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_hours_worked=timedelta(hours=25),
                month=self.month,
            ).exists()
        )

    def test_user_create_audit_time_summary_whithout_worked_hours_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "month": self.month.pk,
            "scheduled-hours": "30",
            "observations": "Observaciones Ejemplo",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas trabajadas ingresadas no pueden estar vacías."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                total_scheduled_hours=timedelta(hours=30),
                observations="Invalid",
                month=self.month,
            ).exists()
        )

    def test_user_create_summary_hours_worked_invalid_worked_hours_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "Invalid",
            "observations": "Invalid",
            "month": self.month.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_summary_hours_worked")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas trabajadas no pueden contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_scheduled_hours=timedelta(hours=30),
                month=self.month,
            ).exists()
        )

    def test_user_can_create_summary_hours_worked_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_summary_hours_worked")

        form_data = {
            "audit": self.audit.pk,
            "month": self.month.pk,
            "scheduled-hours": "48",
            "worked-hours": "34",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("summary_worked_hours_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Resumen de Horas Trabajadas creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=timedelta(hours=48),
                total_hours_worked=timedelta(hours=34),
            ).exists()
        )

    def test_user_can_delete_summary_hours_worked(self):
        self.client.login(username="auditor", password="password123")

        summary_hours_worked_to_delete = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            month=self.month,
            total_scheduled_hours=format_duration_field(55, "hours"),
            total_hours_worked=format_duration_field(50, "hours"),
            observations="Observaciones to update",
        )

        get_url = reverse(
            "delete_summary_hours_worked",
            kwargs={"id": summary_hours_worked_to_delete.pk},
        )

        response = self.client.post(get_url)

        self.assertEqual(response.status_code, 302)

        expected_redirect_url = reverse("summary_worked_hours_table")
        self.assertRedirects(response, expected_redirect_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Resumen de Horas Trabajadas eliminado exitosamente."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                id=summary_hours_worked_to_delete.pk
            ).exists()
        )

    def test_user_delete_summary_hours_worked_no_exits_id(self):
        self.client.login(username="auditor", password="password123")

        summary_hours_worked_to_delete = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            month=self.month,
            total_scheduled_hours=format_duration_field(55, "hours"),
            total_hours_worked=format_duration_field(50, "hours"),
            observations="Observaciones to update",
        )

        post_url = reverse(
            "delete_summary_hours_worked",
            kwargs={"id": 333},
        )

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                id=summary_hours_worked_to_delete.pk
            ).exists()
        )

    def test_user_delete_summary_hours_worked_that_its_not_them_own(self):
        self.client.login(username="auditor", password="password123")
        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_delete_summary_audit",
            first_name="other_auditor_for_to_delete_summary_audit",
            last_name="other_auditor_for_to_delete_summary_audit",
            email="other_auditor_for_to_delete_summary_audit@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)

        summary_hours_worked_to_delete = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=other_auditor,
            month=self.month,
            total_scheduled_hours=format_duration_field(55, "hours"),
            total_hours_worked=format_duration_field(50, "hours"),
            observations="Observaciones to update",
        )

        post_url = reverse(
            "delete_summary_hours_worked",
            kwargs={"id": summary_hours_worked_to_delete.pk},
        )

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                id=summary_hours_worked_to_delete.pk
            ).exists()
        )

    def test_user_can_update_summary_hours_worked(self):
        self.client.login(username="auditor", password="password123")

        summary_hours_worked_to_update = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            month=self.month2,
            total_scheduled_hours=format_duration_field(1, "hours"),
            total_hours_worked=format_duration_field(1, "hours"),
            observations="Lorem ipsum dolor...",
        )

        post_url = reverse(
            "summary_hours_worked", kwargs={"id": summary_hours_worked_to_update.pk}
        )

        form_data = {
            "month": self.month.pk,
            "scheduled-hours": "85",
            "worked-hours": "80",
            "observations": "Updated Observations",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "85 horas")
        self.assertContains(response, "80 horas")
        self.assertContains(response, "Enero")
        self.assertContains(response, "Updated Observations")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Resumen de horas trabajadas actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=format_duration_field(85, "hours"),
                total_hours_worked=format_duration_field(80, "hours"),
                observations="Updated Observations",
            ).exists()
        )

    def test_user_update_summary_hours_worked_invalid_worked_hours_error(self):
        self.client.login(username="auditor", password="password123")
        post_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        form_data = {
            "month": self.month.pk,
            "scheduled-hours": "85",
            "worked-hours": "Invalid",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.summary_hours_worked.month)
        self.assertContains(response, self.summary_hours_worked.observations)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas trabajadas no pueden contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                month=self.month,
                total_scheduled_hours=timedelta(hours=85),
            ).exists()
        )

    def test_user_update_summary_hours_worked_invalid_scheduled_hours_error(self):
        self.client.login(username="auditor", password="password123")
        post_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        form_data = {
            "month": self.month.pk,
            "scheduled-hours": "Invalid",
            "worked-hours": "85",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, self.summary_hours_worked.month)
        self.assertContains(response, self.summary_hours_worked.observations)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Las horas programadas no pueden contener letras ni carácteres especiales, solo números."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                month=self.month,
                total_hours_worked=timedelta(hours=85),
            ).exists()
        )

    def test_user_update_summary_hours_worked_without_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                observations="Invalid",
                audit=self.audit,
            ).exists()
        )

    def test_user_create_summary_hours_worked_invalid_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
            "month": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                audit=self.audit,
            ).exists()
        )

    def test_user_create_summary_hours_worked_does_not_exits_month_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse(
            "summary_hours_worked", kwargs={"id": self.summary_hours_worked.pk}
        )
        form_data = {
            "audit": self.audit.pk,
            "scheduled-hours": "30",
            "worked-hours": "25",
            "observations": "Invalid",
            "month": 3333333,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El mes ingresado no existe o es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                observations="Invalid",
                total_scheduled_hours=timedelta(hours=30),
                total_hours_worked=timedelta(hours=25),
                audit=self.audit,
            ).exists()
        )

    def test_user_can_update_summary_hours_worked_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        summary_hours_worked_to_update = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=self.auditor,
            month=self.month2,
            total_scheduled_hours=format_duration_field(1, "hours"),
            total_hours_worked=format_duration_field(1, "hours"),
            observations="Lorem ipsum dolor...",
        )
        post_url = reverse(
            "summary_hours_worked", kwargs={"id": summary_hours_worked_to_update.pk}
        )
        form_data = {
            "month": self.month2.pk,
            "scheduled-hours": "85",
            "worked-hours": "80",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "85")
        self.assertContains(response, "80")
        self.assertContains(response, "Marzo")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Resumen de horas trabajadas actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            SummaryHoursWorked.objects.filter(
                month=self.month2,
                total_scheduled_hours=format_duration_field(85, "hours"),
                total_hours_worked=format_duration_field(80, "hours"),
            ).exists()
        )

    def test_user_update_summary_hours_worked_that_is_not_his_owned(self):
        self.client.login(username="auditor", password="password123")

        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_update_summary_audit",
            first_name="other_auditor_for_to_update_summary_audit",
            last_name="other_auditor_for_to_update_summary_audit",
            email="other_auditor_for_to_update_summary_audit@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)

        self.client.login(username="auditor", password="password123")

        summary_hours_worked_to_update = SummaryHoursWorked.objects.create(
            audit=self.audit,
            auditor=other_auditor,
            month=self.month2,
            total_scheduled_hours=format_duration_field(1, "hours"),
            total_hours_worked=format_duration_field(1, "hours"),
            observations="Lorem ipsum dolor...",
        )

        post_url = reverse(
            "summary_hours_worked", kwargs={"id": summary_hours_worked_to_update.pk}
        )

        form_data = {
            "month": self.month.pk,
            "scheduled-hours": "85",
            "worked-hours": "80",
            "observations": "Updated Observations",
        }
        response = self.client.post(post_url, data=form_data)
        self.assertEqual(response.status_code, 404)

        self.assertFalse(
            SummaryHoursWorked.objects.filter(
                month=self.month,
                total_scheduled_hours=format_duration_field(85, "hours"),
                total_hours_worked=format_duration_field(80, "hours"),
                observations="Updated Observations",
            ).exists()
        )


class WorkingPapersStatusTestCase(TestCase):
    def setUp(self):
        self.auditor_manager = User.objects.create_user(
            username="auditor_manager",
            first_name="auditor_manager",
            last_name="auditor_manager",
            email="auditor_manager@gmail.com",
            role="audit_manager",
            password="password123",
        )

        self.auditor = User.objects.create_user(
            username="auditor",
            first_name="auditor",
            last_name="auditor",
            email="auditor@gmail.com",
            password="password123",
        )

        self.audit = Audit.objects.create(
            title="Título ejemplo Auditoría 1",
            description="Descripsión ejemplo de Auditoría 1",
            company="Compañía ejemplo Auditoria 1",
            audit_manager=self.auditor_manager,
        )

        self.audit2 = Audit.objects.create(
            title="Título ejemplo Auditoría 2",
            description="Descripsión ejemplo de Auditoría 2",
            company="Compañía ejemplo Auditoria 2",
            audit_manager=self.auditor_manager,
        )
        self.audit.assigned_users.add(self.auditor)

        self.current_status = CurrentStatus.objects.create(
            name="Inicializado"
        )

        self.current_status2 = CurrentStatus.objects.create(
            name="Terminado"
        )
        self.working_paper_status = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-001",
            working_papers="Documento 1",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Sin observaciones.",
            current_status=self.current_status,
        )

    def test_string_representation(self):
        self.assertEqual(str(self.working_paper_status), "Documento 1 - Inicializado")

    def test_formatted_dates(self):
        self.assertEqual(
            self.working_paper_status.formatted_start_date(), "1 de enero de 2024"
        )
        self.assertEqual(
            self.working_paper_status.formatted_end_date(), "5 de enero de 2024"
        )

    def test_working_papers_status_can_be_updated(self):
        working_papers_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-002",
            working_papers="Documento 2",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Sin observaciones.",
            current_status=self.current_status,
        )

        auditor_manager_for_to_update = User.objects.create_user(
            username="auditor_manager_for_to_update",
            first_name="auditor_manager_for_to_update",
            last_name="auditor_manager_for_to_update",
            email="auditor_manager_for_to_update@gmail.com",
            role="audit_manager",
            password="password123",
        )

        auditor_for_to_update = User.objects.create_user(
            username="auditor_for_to_update",
            first_name="auditor_for_to_update",
            last_name="auditor_for_to_update",
            email="auditor_for_to_update@gmail.com",
            password="password123",
        )

        audit_for_to_update = Audit.objects.create(
            title="Título ejemplo Auditoría 2",
            description="Descripsión ejemplo de Auditoría 2",
            company="Compañía ejemplo Auditoria 2",
            audit_manager=auditor_manager_for_to_update,
        )

        audit_for_to_update.assigned_users.add(auditor_for_to_update)

        new_reference = "WP-003"
        new_working_papers = "Nuevos Documentso"
        new_start_date = timezone.make_aware(datetime(2024, 5, 2, 0, 0))

        new_end_date = timezone.make_aware(datetime(2024, 7, 4, 0, 0))

        new_observations = "Nuevas Observaciones"
        working_papers_status_to_update.auditor = auditor_for_to_update
        working_papers_status_to_update.audit = audit_for_to_update
        working_papers_status_to_update.reference = new_reference
        working_papers_status_to_update.working_papers = new_working_papers
        working_papers_status_to_update.start_date = new_start_date
        working_papers_status_to_update.end_date = new_end_date
        working_papers_status_to_update.observations = new_observations
        working_papers_status_to_update.current_status = self.current_status2

        self.assertEqual(working_papers_status_to_update.auditor, auditor_for_to_update)
        self.assertEqual(working_papers_status_to_update.audit, audit_for_to_update)
        self.assertEqual(working_papers_status_to_update.reference, new_reference)
        self.assertEqual(
            working_papers_status_to_update.working_papers, new_working_papers
        )
        self.assertEqual(working_papers_status_to_update.start_date, new_start_date)
        self.assertEqual(working_papers_status_to_update.end_date, new_end_date)
        self.assertEqual(working_papers_status_to_update.observations, new_observations)
        self.assertEqual(
            working_papers_status_to_update.current_status, self.current_status2
        )

    def test_working_papers_status_can_be_deleted(self):
        working_papers_status_to_delete = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-003",
            working_papers="Documento 3",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Sin observaciones.",
            current_status=self.current_status,
        )

        working_papers_status_to_delete.delete()

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-003",
                working_papers="Documento 3",
                start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
                observations="Sin observaciones.",
                current_status=self.current_status,
            ).exists()
        )

    def test_working_papers_status_table_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "status_of_work_papers_table",
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.working_paper_status.reference)
        self.assertContains(response, self.working_paper_status.working_papers)
        self.assertContains(response, self.working_paper_status.observations)
        self.assertContains(response, "Estado de Papeles de Trabajo")
        self.assertContains(response, "Crear Registro")
        self.assertContains(response, self.working_paper_status.formatted_end_date())
        self.assertContains(response, self.working_paper_status.formatted_start_date())
        self.assertContains(response, self.working_paper_status.current_status)

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_working_papers_status_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse(
            "status_of_work_papers", kwargs={"id": self.working_paper_status.pk}
        )
        response = self.client.get(get_url)
        self.assertContains(response, self.working_paper_status.reference)
        self.assertContains(response, self.working_paper_status.working_papers)
        self.assertContains(response, self.working_paper_status.observations)
        self.assertContains(response, "Detalles del Papel de Trabajo")
        self.assertContains(response, self.working_paper_status.formatted_end_date())
        self.assertContains(response, self.working_paper_status.formatted_start_date())
        self.assertContains(response, self.working_paper_status.current_status)

        self.assertEqual(response.status_code, 200)

    def test_user_can_access_to_create_working_papers_status_page(self):
        self.client.login(username="auditor", password="password123")
        get_url = reverse("create_status_of_work_papers")
        response = self.client.get(get_url)
        self.assertContains(response, "Auditoría")
        self.assertContains(response, "Referencia")
        self.assertContains(response, "Papeles de trabajo")
        self.assertContains(response, "Guardar")
        self.assertContains(response, "Observaciones")
        self.assertContains(response, "Estado")
        self.assertContains(response, "Fecha de Inicio")

        self.assertEqual(response.status_code, 200)

    def test_user_can_create_working_papers_status(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "WP-005",
            "working-papers": "Documento 5",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Observaciones ejemplo",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("status_of_work_papers_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Estado de Papeles de Trabajo creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-005",
                working_papers="Documento 5",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Observaciones ejemplo",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_can_create_working_papers_status_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "WP-005",
            "working-papers": "Documento 5",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("status_of_work_papers_table")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Estado de Papeles de Trabajo creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-005",
                working_papers="Documento 5",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_without_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no existe."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_invalid_audit_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": "Invalid",
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La auditoría ingresada no existe."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_without_reference_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La referencia no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_without_working_papers_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Los papeles de trabajo no pueden estar vacíos."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_without_start_date_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La fecha de inicio no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_start_date_invalid_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "Invalid",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La fecha de inicio ingresada debe ser formato 'YYYY-MM-DD'."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_without_end_date_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La fecha de finalización no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_end_date_invalid_error(self):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "Invalid",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La fecha de finalización ingresada debe ser formato 'YYYY-MM-DD'."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_create_working_papers_status_end_date_without_current_status_error(
        self,
    ):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "Invalid",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_create_working_papers_status_invalid_current_status_error(
        self,
    ):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "2024-5-25",
            "observations": "Invalid",
            "current-status": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual ingresado es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_create_working_papers_status_no_exits_current_status_error(
        self,
    ):
        self.client.login(username="auditor", password="password123")

        post_url = reverse("create_status_of_work_papers")

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "2024-5-25",
            "observations": "Invalid",
            "current-status": 9999,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("create_status_of_work_papers")
        self.assertRedirects(response, expected_redirect_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual ingresado es inválido o no existe."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_can_update_working_papers_status(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "WP-010",
            "working-papers": "Documento 10",
            "start-date": "2024-7-3",
            "end-date": "2024-7-22",
            "observations": "Observaciones ejemplo Actualizada",
            "current-status": self.current_status2.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-010")
        self.assertContains(response, "Documento 10")
        self.assertContains(response, "Observaciones ejemplo Actualizada")
        self.assertContains(response, "3 de julio de 2024")
        self.assertContains(response, "22 de julio de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Estado de Papeles de Trabajo actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-010",
                working_papers="Documento 10",
                start_date=timezone.make_aware(datetime(2024, 7, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 7, 22, 0, 0)),
                observations="Observaciones ejemplo Actualizada",
                current_status=self.current_status2,
            )
        )

    def test_user_can_update_working_papers_status_whithout_observations(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "WP-010",
            "working-papers": "Documento 10",
            "start-date": "2024-7-3",
            "end-date": "2024-7-22",
            "observations": "Observaciones ejemplo Actualizada",
            "current-status": self.current_status2.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-010")
        self.assertContains(response, "Documento 10")
        self.assertContains(response, "Observaciones ejemplo Actualizada")
        self.assertContains(response, "3 de julio de 2024")
        self.assertContains(response, "22 de julio de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Estado de Papeles de Trabajo actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-010",
                working_papers="Documento 10",
                start_date=timezone.make_aware(datetime(2024, 7, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 7, 22, 0, 0)),
                observations="Observaciones ejemplo Actualizada",
                current_status=self.current_status2,
            )
        )

    def test_user_update_working_papers_status_that_not_is_them_own(self):
        self.client.login(username="auditor", password="password123")
        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_update_working",
            first_name="other_auditor_for_to_update_working",
            last_name="other_auditor_for_to_update_working",
            email="other_auditor_for_to_update_working@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=other_auditor,
            audit=self.audit,
            reference="WP-087",
            working_papers="Documento 87",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status2,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "WP-010",
            "working-papers": "Documento 10",
            "start-date": "2024-7-3",
            "end-date": "2024-7-22",
            "observations": "Observaciones ejemplo Actualizada",
            "current-status": self.current_status2.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 404)

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-010",
                working_papers="Documento 10",
                start_date=timezone.make_aware(datetime(2024, 7, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 7, 22, 0, 0)),
                observations="Observaciones ejemplo Actualizada",
                current_status=self.current_status2,
            )
        )

    def test_user_update_working_papers_status_without_reference_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La referencia no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_without_working_papers_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "WP-020",
            "start-date": "2024-4-3",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Los papeles de trabajo no pueden estar vacíos."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-020",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_without_start_date_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "Invalid",
            "working-papers": "Invalid",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La fecha de inicio no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_start_date_invalid_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "Invalid",
            "end-date": "2024-5-22",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La fecha de inicio ingresada debe ser formato 'YYYY-MM-DD'."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                end_date=timezone.make_aware(datetime(2024, 5, 22, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_without_end_date_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-3",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "La fecha de finalización no puede estar vacía."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 3, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_end_date_invalid_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "Invalid",
            "observations": "Invalid",
            "current-status": self.current_status.pk,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "La fecha de finalización ingresada debe ser formato 'YYYY-MM-DD'."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
                current_status=self.current_status,
            ).exists()
        )

    def test_user_update_working_papers_status_end_date_without_current_status_error(
        self,
    ):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "Invalid",
            "observations": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual no puede estar vacío."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_update_working_papers_status_invalid_current_status_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "2024-5-25",
            "observations": "Invalid",
            "current-status": "Invalid",
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual ingresado es inválido."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_update_working_papers_status_no_exits_current_status_error(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_update = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-007",
            working_papers="Documento 7",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status,
        )

        post_url = reverse(
            "status_of_work_papers", kwargs={"id": working_paper_status_to_update.pk}
        )

        form_data = {
            "audit": self.audit.pk,
            "reference": "Invalid",
            "working-papers": "Invalid",
            "start-date": "2024-4-23",
            "end-date": "2024-5-25",
            "observations": "Invalid",
            "current-status": 9999,
        }
        response = self.client.post(post_url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WP-007")
        self.assertContains(response, "Documento 7")
        self.assertContains(response, "Observaciones ejemplo")
        self.assertContains(response, "1 de enero de 2024")
        self.assertContains(response, "5 de enero de 2024")
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El estado actual ingresado es inválido o no existe."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="Invalid",
                working_papers="Invalid",
                start_date=timezone.make_aware(datetime(2024, 4, 23, 0, 0)),
                observations="Invalid",
            ).exists()
        )

    def test_user_can_delete_working_papers_status(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_delete = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-087",
            working_papers="Documento 87",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status2,
        )

        post_url = reverse(
            "delete_status_of_work_papers",
            kwargs={"id": working_paper_status_to_delete.pk},
        )

        response = self.client.post(post_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Estado de Papeles de Trabajo eliminado exitosamente."
                for message in messages
            )
        )

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-087",
                working_papers="Documento 87",
                start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
                observations="Observaciones ejemplo",
                current_status=self.current_status2,
            ).exists()
        )

    def test_user_can_delete_working_papers_status(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_delete = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-087",
            working_papers="Documento 87",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status2,
        )

        post_url = reverse(
            "delete_status_of_work_papers",
            kwargs={"id": working_paper_status_to_delete.pk},
        )

        response = self.client.post(post_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message
                == "Estado de Papeles de Trabajo eliminado exitosamente."
                for message in messages
            )
        )

        self.assertEqual(response.status_code, 302)
        expected_redirect_url = reverse("status_of_work_papers_table")
        self.assertRedirects(response, expected_redirect_url)

        self.assertFalse(
            WorkingPapersStatus.objects.filter(
                auditor=self.auditor,
                audit=self.audit,
                reference="WP-087",
                working_papers="Documento 87",
                start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
                observations="Observaciones ejemplo",
                current_status=self.current_status2,
            ).exists()
        )

    def test_user_delete_working_papers_status_that_is_not_them_own(self):
        self.client.login(username="auditor", password="password123")
        other_auditor = User.objects.create_user(
            username="other_auditor_for_to_delete_working",
            first_name="other_auditor_for_to_delete_working",
            last_name="other_auditor_for_to_delete_working",
            email="other_auditor_for_to_delete_working@gmail.com",
            password="password123",
        )

        self.audit.assigned_users.add(other_auditor)
        working_paper_status_to_delete = WorkingPapersStatus.objects.create(
            auditor=other_auditor,
            audit=self.audit,
            reference="WP-087",
            working_papers="Documento 87",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status2,
        )

        post_url = reverse(
            "delete_status_of_work_papers",
            kwargs={"id": working_paper_status_to_delete.pk},
        )

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=other_auditor,
                audit=self.audit,
                reference="WP-087",
                working_papers="Documento 87",
                start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
                end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
                observations="Observaciones ejemplo",
                current_status=self.current_status2,
            ).exists()
        )

    def test_user_delete_working_papers_status_invalid_id(self):
        self.client.login(username="auditor", password="password123")

        working_paper_status_to_delete = WorkingPapersStatus.objects.create(
            auditor=self.auditor,
            audit=self.audit,
            reference="WP-087",
            working_papers="Documento 87",
            start_date=timezone.make_aware(datetime(2024, 1, 1, 0, 0)),
            end_date=timezone.make_aware(datetime(2024, 1, 5, 0, 0)),
            observations="Observaciones ejemplo",
            current_status=self.current_status2,
        )

        post_url = reverse(
            "delete_status_of_work_papers",
            kwargs={"id": 333333},
        )

        response = self.client.post(post_url)

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            WorkingPapersStatus.objects.filter(
                auditor=working_paper_status_to_delete.auditor,
                audit=working_paper_status_to_delete.audit,
                reference=working_paper_status_to_delete.reference,
                working_papers=working_paper_status_to_delete.working_papers,
                start_date=working_paper_status_to_delete.start_date,
                end_date=working_paper_status_to_delete.end_date,
                observations=working_paper_status_to_delete.observations,
                current_status=working_paper_status_to_delete.current_status,
            ).exists()
        )
"""


class AuditMarksTestCase(TestCase):
    def setUp(self):
        self.auditor_role = Roles.objects.create(name="auditor", verbose_name="Auditor")
        self.superuser = User.objects.create_superuser(
            username="superuser",
            first_name="superuser",
            last_name="superuser",
            email="superuser@gmail.com",
            password="password123",
            role=self.auditor_role,
        )

        self.audit_mark = AuditMarks.objects.create(
            image="https://png.pngtree.com/png-clipart/20200801/ourmid/pngtree-black-ring-png-image_2319165.png",
            name="Revisión Documental",
            description="Revisado los documentos",
        )

        self.user = User.objects.create_user(
            username="user",
            first_name="user",
            last_name="user",
            email="user@gmail.com",
            password="password123",
            role=self.auditor_role,
        )

    def test_audit_mark_can_be_created(self):
        name = "Sumado"
        image = "https://cdn-icons-png.flaticon.com/512/33/33281.png"
        description = "Está sumado"

        AuditMarks.objects.create(name=name, image=image, description=description)

        self.assertTrue(
            AuditMarks.objects.filter(
                name=name, image=image, description=description
            ).exists()
        )

    def test_audit_mark_can_be_updated(self):
        audit_mark_to_update = AuditMarks.objects.create(
            name="To Updated", image="To Update", description="To Upadte"
        )

        audit_mark_to_update.name = "Updated Name"
        audit_mark_to_update.description = "Updated Description"
        audit_mark_to_update.image = "Updated Image"

        audit_mark_to_update.save()
        self.assertTrue(
            AuditMarks.objects.filter(
                name="Updated Name",
                description="Updated Description",
                image="Updated Image",
            ).exists()
        )

    def test_audit_mark_can_be_deleted(self):
        audit_mark_to_delete = AuditMarks.objects.create(
            name="To Delete", image="To Delete", description="To Delete"
        )

        audit_mark_to_delete.delete()

        self.assertFalse(
            AuditMarks.objects.filter(
                name="To Delete", image="To Delete", description="To Delete"
            )
        )

    def test_user_can_access_to_audit_marks_table_without_actions(self):
        self.client.login(email="user@gmail.com", password="password123")

        url = reverse(
            "audit_marks",
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Debes hacer Clic para abrir en el nombre del archivo, para que puedas visualizar y trabajar la plantilla hacerle cambios, guardar, descargar en Excel o PDF, enviar el archivo por correo y hacer videollamadas.",
        )
        self.assertNotContains(response, "Añadir Marca")
        self.assertNotContains(response, "Ver Más")

    def test_super_user_can_access_to_audit_marks_table_with_actions_and_add_button(
        self,
    ):
        self.client.login(email="superuser@gmail.com", password="password123")

        url = reverse(
            "audit_marks",
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Debes hacer Clic para abrir en el nombre del archivo, para que puedas visualizar y trabajar la plantilla hacerle cambios, guardar, descargar en Excel o PDF, enviar el archivo por correo y hacer videollamadas.",
        )
        self.assertContains(response, "Añadir Marca")
        self.assertContains(response, "Ver Más")

    def test_user_can_not_access_to_audit_mark_details_page(self):
        self.client.login(email="user@gmail.com", password="password123")

        url = reverse("audit_mark", kwargs={"id": 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_superuser_can_access_to_audit_mark_details_page(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        url = reverse("audit_mark", kwargs={"id": 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guardar")
        self.assertContains(response, "Descripción")
        self.assertContains(response, "Nombre")
        self.assertContains(response, "URL Ícono")

    def test_superuser_can_update_an_audit_mark(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        form_data = {
            "name": "Updated Mark",
            "description": "Updated Mark",
            "image": "Updated Mark",
        }
        url = reverse("audit_mark", kwargs={"id": 1})
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Marca de Auditoría actualizada exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            AuditMarks.objects.filter(
                name="Updated Mark", description="Updated Mark", image="Updated Mark"
            )
        )

    def test_user_can_not_update_and_audit_mark(self):
        self.client.login(email="user@gmail.com", password="password123")

        form_data = {
            "name": "Updated Mark",
            "description": "Updated Mark",
            "image": "Updated Mark",
        }
        url = reverse("audit_mark", kwargs={"id": 1})
        response = self.client.post(url, data=form_data)
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_delete_an_audit_mark(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        audit_mark_to_delete = AuditMarks.objects.create(
            name="To Delete", description="To Delete", image="To Delete"
        )
        url = reverse("delete_audit_mark", kwargs={"id": audit_mark_to_delete.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        expected_url = reverse("audit_marks")
        self.assertRedirects(response, expected_url)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Marca de Auditoría eliminada exitosamente."
                for message in messages
            )
        )

        self.assertFalse(
            AuditMarks.objects.filter(
                name="To Delete",
                description="To Delete",
                image="To Delete",
                id=audit_mark_to_delete.pk,
            ).exists()
        )

    def test_user_can_not_delete_and_audit_mark(self):
        self.client.login(email="user@gmail.com", password="password123")

        audit_mark_to_delete = AuditMarks.objects.create(
            name="To Delete", description="To Delete", image="To Delete"
        )
        url = reverse("delete_audit_mark", kwargs={"id": audit_mark_to_delete.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)


class CurrencyTypesTestCase(TestCase):
    def setUp(self):
        self.auditor_role = Roles.objects.create(name="auditor", verbose_name="Auditor")
        self.superuser = User.objects.create_superuser(
            username="superuser",
            first_name="superuser",
            last_name="superuser",
            email="superuser@gmail.com",
            password="password123",
            role=self.auditor_role,
        )

        self.country = Country.objects.create(
            name="united_states",
            verbose_name="Estados Unidos",
            alpha2_code="US",
            alpha3_code="USA",
        )
        self.currency_type = CurrencyType.objects.create(
            name="Dólar", currency="$", code="USD", country=self.country
        )

        self.user = User.objects.create_user(
            username="user",
            first_name="user",
            last_name="user",
            email="user@gmail.com",
            password="password123",
            role=self.auditor_role,
        )

    def test_user_can_access_to_currency_types_without_actions(self):
        self.client.login(email="user@gmail.com", password="password123")

        url = reverse("currency_types")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tipos de Monedas")
        self.assertContains(response, "Dólar")
        self.assertContains(response, "USD")

        self.assertNotContains(response, "Añadir Tipo de Moneda")
        self.assertNotContains(response, "Ver Más")

    def test_superuser_can_access_to_currency_types_with_actions(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        url = reverse("currency_types")

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tipos de Monedas")
        self.assertContains(response, "Dólar")
        self.assertContains(response, "USD")

        self.assertContains(response, "Añadir Tipo de Moneda")
        self.assertContains(response, "Ver Más")

    def test_superuser_can_access_to_currency_type_page(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        url = reverse("currency_type", kwargs={"id": 1})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "Dólar")
        self.assertContains(response, "USD")

    def test_user_can_not_access_to_currency_type_page(self):
        self.client.login(email="user@gmail.com", password="password123")

        url = reverse("currency_type", kwargs={"id": 1})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_create_an_currency_type(self):
        self.client.login(email="superuser@gmail.com", password="password123")
        new_country = Country.objects.create(
            name="New cc",
            verbose_name="New ccc",
            alpha2_code="CC",
            alpha3_code="CCC",
        )

        form_data = {
            "country": new_country.pk,
            "name": "Created Name",
            "currency": "Created Currency",
            "code": "Created Code",
        }
        url = reverse("create_currency_type")

        response = self.client.post(url, data=form_data)

        expected_url = reverse("currency_types")

        self.assertEqual(response.status_code, 302)

        self.assertRedirects(response, expected_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Tipo de moneda creado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            CurrencyType.objects.filter(
                country=new_country,
                name="Created Name",
                currency="Created Currency",
                code="Created Code",
            ).exists()
        )

    def test_user_can_not_create_an_currency_type(self):
        self.client.login(email="user@gmail.com", password="password123")

        form_data = {
            "country": self.country.pk,
            "name": "New Name",
            "currency": "New Currency",
            "code": "New Code",
        }
        url = reverse("create_currency_type")

        response = self.client.get(url, data=form_data)

        self.assertEqual(response.status_code, 404)

    def test_superuser_can_update_an_currency_type(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        new_country = Country.objects.create(
            name="New Country",
            verbose_name="New Country",
            alpha2_code="NC",
            alpha3_code="NCY",
        )
        form_data = {
            "country": new_country.pk,
            "name": "New Name",
            "currency": "New Currency",
            "code": "New Code",
        }
        url = reverse("currency_type", kwargs={"id": self.currency_type.pk})

        response = self.client.post(url, data=form_data)

        self.assertEqual(response.status_code, 200)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Tipo de moneda actualizado exitosamente."
                for message in messages
            )
        )

        self.assertTrue(
            CurrencyType.objects.filter(
                country=new_country,
                name="New Name",
                currency="New Currency",
                code="New Code",
            )
        )

    def test_user_can_not_update_an_currency_type(self):
        self.client.login(email="superuser@gmail.com", password="password123")

        new_country = Country.objects.create(
            name="New Country",
            verbose_name="New Country",
            alpha2_code="NC",
            alpha3_code="NCY",
        )
        form_data = {
            "country": new_country.pk,
            "name": "New Name",
            "currency": "New Currency",
            "code": "New Code",
        }
        url = reverse("currency_type", kwargs={"id": 1})

        response = self.client.get(url, data=form_data)

        self.assertEqual(response.status_code, 404)

    def test_superuser_can_delete_an_currency_type(self):
        self.client.login(email="superuser@gmail.com", password="password123")
        currency_type_to_delete = CurrencyType.objects.create(
            name="To Delete",
            country=self.country,
            currency="To Delete",
            code="To Delete",
        )
        url = reverse("delete_currency_type", kwargs={"id": currency_type_to_delete.pk})

        response = self.client.post(url)

        expected_url = reverse("currency_types")

        self.assertEqual(response.status_code, 302)

        self.assertRedirects(response, expected_url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "Tipo de moneda eliminado exitosamente."
                for message in messages
            )
        )

        self.assertFalse(
            CurrencyType.objects.filter(
                name="To Delete",
                country=self.country,
                currency="To Delete",
                code="To Delete",
            )
        )

    def test_user_can_not_update_an_currency_type(self):
        self.client.login(email="user@gmail.com", password="password123")
        currency_type_to_delete = CurrencyType.objects.create(
            name="To Delete",
            country=self.country,
            currency="To Delete",
            code="To Delete",
        )
        url = reverse("currency_type", kwargs={"id": currency_type_to_delete.pk})

        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)
