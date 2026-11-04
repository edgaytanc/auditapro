"""Ajustes solo para pruebas: sin manifiesto de estáticos ni redirecciones SSL."""
from .settings import *  # noqa: F401,F403

STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
SECURE_SSL_REDIRECT = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
