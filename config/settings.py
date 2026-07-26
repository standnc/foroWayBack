# config/settings.py
"""
Django settings for bbforo — Foro Retro BoomBang.
Entorno: LOCAL DEVELOPMENT (con compatibilidad VPS)
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============ CORE ============
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-local-dev-key-change-me")
# ✅ DESPUÉS
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
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
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_RESET_ON_SUCCESS = True
AXES_ONLY_USER_FAILURES = False

# ============ STORAGE (R2 o local) ============
USE_R2 = os.getenv("USE_R2", "False").lower() == "true"

if USE_R2:
    STORAGES = {
        "default": {"BACKEND": "forum.storage_backends.PublicMediaStorage"},
        "staticfiles": {"BACKEND": "forum.storage_backends.StaticStorage"},
    }
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
    STATIC_ROOT = BASE_DIR / "staticfiles"
    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ============ CSP (django-csp 4.x - Comillas explícitas Error #1) ============
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": [
            "'unsafe-inline'",
            "'unsafe-eval'",
            "'self'",
            "https://unpkg.com",
            "https://cdn.jsdelivr.net",
            "https://cdn.tailwindcss.com",
            "https://accounts.google.com/gsi/client",
        ],
        "style-src": [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            "https://cdn.jsdelivr.net",
            "https://cdn.tailwindcss.com",
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
    CSRF_COOKIE_DOMAIN = ".clashbang.forum"

# ============ LOGGING (Condicional LOCAL/VPS - Evita FileNotFoundError) ============
LOG_DIR = BASE_DIR / "logs" if DEBUG else Path("/var/log/django")
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
