# config/settings.py
"""
Django settings for bbforo — Foro Retro BoomBang.
Entorno: LOCAL DEVELOPMENT (con compatibilidad VPS)
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============ CORE ============
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        # Sin esto, un .env que no carga en el VPS arrancaba en silencio con una
        # clave conocida y firmaba sesiones y tokens de reset con ella.
        raise ImproperlyConfigured(
            "SECRET_KEY no está definida y DEBUG=False. Revisa el .env del servidor."
        )
    SECRET_KEY = "django-insecure-local-dev-key-change-me"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

# ============ APPS ============
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Third-party
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.discord",
    "allauth.socialaccount.providers.github",
    "axes",
    "csp",
    "storages",

    # Local
    "accounts",
    "forum",
]

SITE_ID = 1

# ============ MIDDLEWARE ============
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Tras AuthenticationMiddleware: necesita request.user resuelto.
    "forum.middleware.BanEnforcementMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "csp.middleware.CSPMiddleware",
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ============ DATABASE ============
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.sqlite3"),
        # DB_NAME explícito → string (PostgreSQL); sin env → Path relativo (SQLite local)
        "NAME": os.getenv("DB_NAME") or str(BASE_DIR / "db.sqlite3"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ============ AUTH ============
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ============ ALLAUTH ============
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
# T6.1: env var → "mandatory" en prod (allauth NO loguea hasta confirmar email)
#   En local sin env: "none" (no verificación)
#   En .env de prod:  ACCOUNT_EMAIL_VERIFICATION=mandatory
ACCOUNT_EMAIL_VERIFICATION = os.getenv("ACCOUNT_EMAIL_VERIFICATION", "none")
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_CONFIRM_EMAIL_ON_GET = True  # Auto-confirmar al hacer clic en el link del email
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_ADAPTER = "forum.adapter.ForumAccountAdapter"

LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "OAUTH_PKCE_ENABLED": True,
    },
    "github": {
        "SCOPE": ["user"],
    },
}
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = "forum.adapter.ForumSocialAccountAdapter"

# ============ EMAIL (SMTP Resend) ============
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")  # ← Console en local
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.resend.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "resend")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@clashbang.forum")

# ============ AXES (Rate Limiting) ============
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1
AXES_RESET_ON_SUCCESS = True
# Sustituye a AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP / AXES_ONLY_USER_FAILURES,
# deprecados en axes 6.x: bloquea por la combinación usuario + IP.
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]

# ============ STORAGE (R2 o local) ============
USE_R2 = os.getenv("USE_R2", "False").lower() == "true"

# Comunes a ambos modos: collectstatic tiene que encontrar el CSS compilado
# (static/css/app.css, generado por `npm run build:css`) tanto si los estáticos
# acaban en R2 como en disco.
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Los estáticos por R2 dan 403 (Cloudflare "error code: 1014", CNAME cruzado en
# static.clashbang.forum). Afecta a TODO el bucket, no solo al CSS: se ve al
# dejar de cargar Tailwind por CDN. Mientras no se arregle el dominio de R2, los
# sirve Nginx desde el propio dominio (el location /static/ ya existe), que
# además ahorra una petición cross-origin. Las imágenes del archivo siguen en R2
# con sus URLs guardadas en BD, así que no dependen de esto.
STATIC_DESDE_R2 = os.getenv("STATIC_DESDE_R2", "False").lower() == "true"

if USE_R2:
    STORAGES = {
        "default": {"BACKEND": "forum.storage_backends.PublicMediaStorage"},
        # La clave 'staticfiles' es obligatoria (staticfiles.E005); lo que
        # cambia es a dónde escribe collectstatic y de dónde sirve STATIC_URL.
        "staticfiles": (
            {"BACKEND": "forum.storage_backends.StaticStorage"}
            if STATIC_DESDE_R2
            else {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
        ),
    }
    if not STATIC_DESDE_R2:
        STATIC_URL = "/static/"
    AWS_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    AWS_STORAGE_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "")
    AWS_S3_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
    AWS_S3_REGION_NAME = "auto"
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_CUSTOM_DOMAIN = os.environ.get("R2_CUSTOM_DOMAIN", None)
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
else:
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ============ CSP (django-csp 4.x - Comillas explícitas Error #1) ============
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            # Alpine evalúa sus expresiones (x-data, @click…) con new Function,
            # así que necesita unsafe-eval mientras siga en uso. unsafe-inline
            # cae cuando se muevan los <script> inline que quedan en base.html.
            "'unsafe-inline'",
            "'unsafe-eval'",
            "https://cdn.jsdelivr.net",  # Alpine y HTMX
            "https://accounts.google.com/gsi/client",
        ],
        "style-src": [
            "'self'",
            # Tailwind ya no se compila en el navegador: el CSS se sirve desde
            # 'self'. unsafe-inline queda solo por los style="" de las
            # plantillas (barras de progreso y colores de rango dinámicos).
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            # Necesario si los estáticos vuelven a servirse desde R2
            # (STATIC_DESDE_R2=True): sin esto el navegador bloquea la hoja.
            "https://static.clashbang.forum",
        ],
        "img-src": [
            "'self'",
            "data:",
            "https://*.r2.cloudflarestorage.com",
            "https://lh3.googleusercontent.com",
            "https://avatars.githubusercontent.com",
            "https://cdn.discordapp.com",
            "https://static.clashbang.forum",
        ],
        "connect-src": [
            "'self'",
            "https://accounts.google.com",
            "https://discord.com",
            "https://github.com",
            "https://api.github.com",
        ],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "frame-src": [
            "https://accounts.google.com",
            "https://discord.com",
            "https://github.com",
        ],
        "form-action": [
            "'self'",
            "https://accounts.google.com",
            "https://discord.com",
            "https://github.com",
            "https://discordapp.com",
        ],
    },
}

# ============ I18N ============
LANGUAGE_CODE = "es-es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============ SECURITY (Prod hardening - solo activo si DEBUG=False) ============
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = "DENY"
    CSRF_TRUSTED_ORIGINS = [
        "https://clashbang.forum",
        "https://www.clashbang.forum",
        "https://foro.clashbang.forum"
    ]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    ALLAUTH_TRUSTED_PROXY_COUNT = 2
    # Sin CSRF_COOKIE_DOMAIN: compartir la cookie con todo *.clashbang.forum
    # la exponía a static.clashbang.forum, que sirve contenido subido desde R2.
    # No hay ningún POST entre subdominios que lo necesite.

# ============ LOGGING (Condicional LOCAL/VPS - Evita FileNotFoundError) ============
# Se puede forzar con LOG_DIR en .env. Sin él: logs/ en local, /var/log/django en el VPS.
LOG_DIR = Path(os.getenv("LOG_DIR") or (BASE_DIR / "logs" if DEBUG else "/var/log/django"))
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    # Entornos sin permiso sobre /var/log (CI, contenedores, otro servidor):
    # caer a un directorio propio en vez de reventar al importar los settings.
    LOG_DIR = BASE_DIR / "logs"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

_LOG_LEVEL = "DEBUG" if DEBUG else "WARNING"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime}  {levelname:8s}  {name:30s}  {message}",
            "style": "{",
        },
        "simple": {
            "format": "{asctime}  {levelname:8s}  {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
        "require_debug_true": {"()": "django.utils.log.RequireDebugTrue"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "foro.log",  # ← Ruta dinámica
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "include_html": False,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security.csrf": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
        "forum": {
            "handlers": ["file", "console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "accounts": {
            "handlers": ["file", "console"],
            "level": _LOG_LEVEL,
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
