# Archivo: saas_project/settings.py

from pathlib import Path
import os
import locale
from dotenv import load_dotenv

load_dotenv()
locale.setlocale(locale.LC_TIME, "")
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-)dje61c_awppvrn8w_jf%way9ugx@dnmq7pmh8x+e#hg44%xp@")
DEBUG = os.environ.get("DEBUG", "True") == "True"
allowed_hosts = os.environ.get("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [host.strip() for host in allowed_hosts.split(",")] if "," in allowed_hosts else [allowed_hosts]
csrf_trusted_origins_env = os.environ.get("CSRF_TRUSTED_ORIGINS", "")
if csrf_trusted_origins_env:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_origins_env.split(",")]
else:
    CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"] if DEBUG else ["https://sistema.auditapro.com"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "common",
    "users",
    "mfa",
    "notifications",
    "audits",
    "management_auditors",
    "tools",
    "auditoria",
    "user_management",
    "analisis",
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
            os.path.join(BASE_DIR, "common/templates"),
            os.path.join(BASE_DIR, "notifications/templates"),
            os.path.join(BASE_DIR, "users/templates"),
            os.path.join(BASE_DIR, "audits/templates"),
            os.path.join(BASE_DIR, "management_auditors/templates"),
            os.path.join(BASE_DIR, "archivo/templates"),
            os.path.join(BASE_DIR, "tools/templates"),
            os.path.join(BASE_DIR, "auditoria/templates"),
            os.path.join(BASE_DIR, "mfa/templates"), # ¡Línea clave!
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-es"
TIME_ZONE = "UTC"
USE_I18N = True
USE_L10N = True
USE_TZ = False

STATIC_URL = "static/"
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

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

# Configuración del correo electrónico
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = 'Sistema de Auditoría <auditaguatemala@gmail.com>'

if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True


# ---------------------------------------------------------------------------
# Audita Análisis (orquestador, agentes y llenado de papeles de trabajo)
# ---------------------------------------------------------------------------
# Los archivos del cliente se guardan en una carpeta privada, fuera de static/ y media/.
ANALISIS_STORAGE_ROOT = Path(os.environ.get("ANALISIS_STORAGE_ROOT", BASE_DIR / "private_analisis"))

# Límites para que subir archivos y analizar no sobrecargue el servidor.
ANALISIS_MAX_FILE_MB = int(os.environ.get("ANALISIS_MAX_FILE_MB", "100"))        # por archivo
ANALISIS_MAX_TOTAL_MB = int(os.environ.get("ANALISIS_MAX_TOTAL_MB", "400"))      # por corrida
ANALISIS_MAX_FILES = int(os.environ.get("ANALISIS_MAX_FILES", "40"))             # por corrida
ANALISIS_MAX_UNZIPPED_MB = int(os.environ.get("ANALISIS_MAX_UNZIPPED_MB", "600"))  # Excel/Word descomprimido
ANALISIS_MAX_ZIP_RATIO = int(os.environ.get("ANALISIS_MAX_ZIP_RATIO", "100"))    # anti «bomba zip»
ANALISIS_MAX_ROWS = int(os.environ.get("ANALISIS_MAX_ROWS", "100000"))           # filas leídas por archivo
ANALISIS_MAX_PDF_PAGES = int(os.environ.get("ANALISIS_MAX_PDF_PAGES", "300"))

# Cola acotada: pocos trabajadores y un tope de corridas activas (se rechaza lo que exceda).
ANALISIS_MAX_WORKERS = int(os.environ.get("ANALISIS_MAX_WORKERS", "2"))
ANALISIS_MAX_QUEUE = int(os.environ.get("ANALISIS_MAX_QUEUE", "8"))
ANALISIS_MAX_ACTIVE_PER_USER = int(os.environ.get("ANALISIS_MAX_ACTIVE_PER_USER", "2"))
ANALISIS_STALE_MINUTES = int(os.environ.get("ANALISIS_STALE_MINUTES", "20"))
ANALISIS_RUN_INLINE = os.environ.get("ANALISIS_RUN_INLINE", "False") == "True"   # solo pruebas

# Claude (opcional). La clave se lee SOLO del entorno; nunca se guarda en el repositorio.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANALISIS_USE_AI = os.environ.get("ANALISIS_USE_AI", "True") == "True"
ANALISIS_CLAUDE_MODEL = os.environ.get("ANALISIS_CLAUDE_MODEL", "claude-sonnet-5-5")
ANALISIS_AI_TIMEOUT = int(os.environ.get("ANALISIS_AI_TIMEOUT", "60"))
ANALISIS_AI_MAX_CALLS = int(os.environ.get("ANALISIS_AI_MAX_CALLS", "60"))
