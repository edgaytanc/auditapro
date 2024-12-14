from django.test import TestCase, Client


class ArchivoTextCase(TestCase):
    def setUp(self) -> None:
        self.client = Client()
