from pathlib import Path
import os
import locale
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

locale.setlocale(locale.LC_TIME, "")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-)dje61c_awppvrn8w_jf%way9ugx@dnmq7pmh8x+e#hg44%xp@")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", "True") == "True"

# Permitir hosts desde variable de entorno (separados por comas) o todos en desarrollo
allowed_hosts = os.environ.get("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",")] if "," in allowed_hosts else [allowed_hosts]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "common",
    "users",
    "notifications",
    "audits",
    "management_auditors",
    "tools",
    "auditoria",
    "user_management",
    "django_tables2",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "users.middleware.UserDeactivationMiddleware",
    "users.middleware.DemoUserAccessMiddleware",
    "users.middleware.DemoUserExpirationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "saas_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(
                BASE_DIR,
                "common/templates",
            ),
            os.path.join(
                BASE_DIR,
                "notifications/templates",
            ),
            os.path.join(
                BASE_DIR,
                "users/templates",
            ),
            os.path.join(
                BASE_DIR,
                "audits/templates",
            ),
            os.path.join(BASE_DIR, "management_auditors/templates"),
            os.path.join(BASE_DIR, "archivo/templates"),
            os.path.join(BASE_DIR, "tools/templates"),
            os.path.join(BASE_DIR, "auditoria/templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "common.context_processors.breadcrumbs_processor",
                "common.context_processors.aside_navbar_processor",
                "common.context_processors.assigned_audits",
                "common.context_processors.is_choose_new_audit_path",
                "common.context_processors.months_processor",
                "common.context_processors.current_statuses_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "saas_project.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "es-es"
TIME_ZONE = "UTC"

USE_I18N = True
USE_L10N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# URL base para generar enlaces en la aplicación
# En desarrollo: http://localhost:8000
# En producción: https://auditapro.com (o el dominio correspondiente)
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")

BASE_DIR = Path(__file__).resolve().parent.parent

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

# Configuración para servir archivos estáticos en producción con Whitenoise
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "users.User"

LOGIN_URL = "login"

DATE_FORMAT = "j \\de F \\del Y"


AUTHENTICATION_BACKENDS = [
    "users.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

handler404 = "common.views.custom_404"

BREADCRUMBS_TEMPLATE = "common/_breadcrumbs.html"

# Configuraciones de seguridad para HTTPS
# Estas configuraciones solo se aplican cuando DEBUG es False (entorno de producción)
if not DEBUG:
    # Usar variable de entorno para controlar la redirección SSL
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = True  # Cookies de sesión solo se envían a través de HTTPS
    CSRF_COOKIE_SECURE = True  # Cookies CSRF solo se envían a través de HTTPS
    CSRF_TRUSTED_ORIGINS = [os.environ.get("BASE_URL", "https://sistema.auditapro.com")]
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # Aplicar HSTS a subdominios
    SECURE_HSTS_PRELOAD = True  # Permitir precargar en listas HSTS
    SECURE_BROWSER_XSS_FILTER = True  # Activa el filtro XSS en navegadores
    SECURE_CONTENT_TYPE_NOSNIFF = True  # Evita que el navegador adivine el tipo de contenido
