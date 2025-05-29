from django.test import TestCase, Client
from django.contrib.auth import authenticate, logout
from users.models import User
from django.urls import reverse
from django.contrib.messages import get_messages


class UserTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.user1 = User.objects.create_user(
            username="Usuario1",
            first_name="Primer",
            last_name="Usuario",
            email="usuario1@gmail.com",
            password="123user",
        )

        self.user2 = User.objects.create_user(
            username="Usuario2",
            first_name="Segundo",
            last_name="Usuario",
            email="usuario2@gmail.com",
            password="123user",
        )

    def test_user_can_signup(self):
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cree su cuenta")

        form_data = {
            "username": "user",
            "first_name": "Nombre de usuario",
            "last_name": "Apellido de usuario",
            "email": "correodeusuario@usuario.com",
            "password_1": "password",
            "password_2": "password",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 302)
        expected_redirect_url = reverse("user")
        self.assertRedirects(post_response, expected_redirect_url)
        self.assertTrue(User.objects.filter(username="user").exists())

    def test_user_password_do_not_matches_signup(self):
        form_data = {
            "username": "user",
            "first_name": "Nombre de usuario",
            "last_name": "Apellido de usuario",
            "email": "correodeusuario@usuario.com",
            "password_1": "password",
            "password_2": "incorrect",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Las contraseñas no coinciden.")
        self.assertFalse(User.objects.filter(username="user").exists())

    def test_user_no_username_error_signup(self):
        form_data = {
            "first_name": "Nombre de usuario",
            "last_name": "Apellido de usuario",
            "email": "correodeusuario@usuario.com",
            "password_1": "password",
            "password_2": "incorrect",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "El nombre de usuario no puede estar vacío.")
        self.assertFalse(
            User.objects.filter(email="correodeusuario@usuario.com").exists()
        )

    def test_user_no_first_name_error_signup(self):
        form_data = {
            "username": "user",
            "last_name": "Apellido de usuario",
            "email": "correodeusuario@usuario.com",
            "password_1": "password",
            "password_2": "incorrect",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "El primer nombre no puede estar vacío.")
        self.assertFalse(User.objects.filter(username="user").exists())

    def test_user_no_last_name_error_signup(self):
        form_data = {
            "username": "user",
            "first_name": "Nombre de usuario",
            "email": "correodeusuario@usuario.com",
            "password_1": "password",
            "password_2": "incorrect",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "El apellido no puede estar vacío.")
        self.assertFalse(User.objects.filter(username="user").exists())

    def test_user_no_email_error_signup(self):
        form_data = {
            "username": "user",
            "first_name": "Nombre de usuario",
            "last_name": "Apellido de usuario",
            "password_1": "password",
            "password_2": "incorrect",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(
            post_response, "El correo electrónico no puede estar vacío."
        )
        self.assertFalse(User.objects.filter(username="user").exists())

    def test_user_no_passwords_error_signup(self):
        form_data = {
            "username": "user",
            "first_name": "Nombre de usuario",
            "last_name": "Apellido de usuario",
            "email": "correodeusuario@usuario.com",
        }

        url = reverse("signup")
        post_response = self.client.post(url, data=form_data)

        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Las contraseñas no pueden estar vacías.")
        self.assertFalse(User.objects.filter(username="user").exists())

    def test_user_can_login(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Iniciar Sesión")

        form_data = {"email": "usuario1@gmail.com", "password": "123user"}

        post_response = self.client.post(reverse("login"), data=form_data)
        self.assertEqual(post_response.status_code, 302)
        expected_redirect_url = reverse("user")
        self.assertRedirects(post_response, expected_redirect_url)

    def test_user_no_email_error_login(self):
        form_data = {"password": "123user"}

        post_response = self.client.post(reverse("login"), data=form_data)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(
            post_response, "El correo electrónico no puede estar vacío."
        )

    def test_user_no_password_error_login(self):
        form_data = {"email": "usuario1@gmail.com"}

        post_response = self.client.post(reverse("login"), data=form_data)
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Las contraseñas no pueden estar vacías.")

    def test_user_can_access_to_user_profile_view(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("user"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Información de Usuario")

    def test_user_can_update_them_username(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("user"))

        self.assertEqual(response.status_code, 200)

        form_data = {
            "value": "new_username",
        }

        url = reverse("edit_field", kwargs={"field": "username"})

        post_response = self.client.post(url, form_data)

        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse("user"))

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El campo se ha actualizado correctamente."
                for message in messages
            )
        )

        self.assertTrue(User.objects.filter(username="new_username").exists())

    def test_user_can_update_them_first_name(self):
        self.client.force_login(self.user1)

        form_data = {
            "value": "new_first_name",
        }

        url = reverse("edit_field", kwargs={"field": "first_name"})

        post_response = self.client.post(url, form_data)

        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse("user"))

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El campo se ha actualizado correctamente."
                for message in messages
            )
        )

        self.assertTrue(User.objects.filter(first_name="new_first_name").exists())

    def test_user_can_update_them_last_name(self):
        self.client.force_login(self.user1)

        form_data = {
            "value": "new_last_name",
        }

        url = reverse("edit_field", kwargs={"field": "last_name"})

        post_response = self.client.post(url, form_data)

        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse("user"))

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El campo se ha actualizado correctamente."
                for message in messages
            )
        )

        self.assertTrue(User.objects.filter(last_name="new_last_name").exists())

    def test_user_can_update_them_email(self):
        self.client.force_login(self.user1)

        form_data = {
            "value": "new_email",
        }

        url = reverse("edit_field", kwargs={"field": "email"})

        post_response = self.client.post(url, form_data)

        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse("user"))

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El campo se ha actualizado correctamente."
                for message in messages
            )
        )

        self.assertTrue(User.objects.filter(email="new_email").exists())

    def test_user_can_update_them_password(self):
        self.client.force_login(self.user1)

        form_data = {
            "value": "new_password",
        }

        url = reverse("edit_field", kwargs={"field": "password"})

        post_response = self.client.post(url, form_data)
        self.assertEqual(post_response.status_code, 302)
        self.assertRedirects(post_response, reverse("user"))

        messages = list(get_messages(post_response.wsgi_request))
        self.assertTrue(
            any(
                message.message == "El campo se ha actualizado correctamente."
                for message in messages
            )
        )

        self.user1.refresh_from_db()

        self.assertTrue(self.user1.check_password("new_password"))
