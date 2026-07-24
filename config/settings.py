"""
Django settings for bbforo — Foro Retro BoomBang.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ============ CORE ============
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "localhost").split(",")]

# ============ APPS ============
INSTALLED_APPS = [
    # Django
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
        "NAME": os.getenv("DB_NAME", "foro.db"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# ============ AUTH ============
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
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
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_SESSION_REMEMBER = True

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
    STATIC_URL = "static/"
    STATIC_ROOT = BASE_DIR / "staticfiles"
    MEDIA_URL = "media/"
    MEDIA_ROOT = BASE_DIR / "media"

# ============ CSP ============
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'unsafe-inline'", 
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
        "connect-src": ["'self'", "https://accounts.google.com"],
        "font-src": ["'self'", "https://fonts.gstatic.com"],
        "frame-src": ["https://accounts.google.com"],
        "form-action": ["'self'"],
    },
}

# ============ I18N ============
LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Madrid"
USE_I18N = True
USE_TZ = True

# ============ DEFAULT ============
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============ SECURITY (prod hardening) ============
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
    CSRF_TRUSTED_ORIGINS = ["https://clashbang.forum", "https://www.clashbang.forum", "https://foro.clashbang.forum"]
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    ALLAUTH_TRUSTED_PROXY_COUNT = 2
ACCOUNT_ADAPTER = "forum.adapter.ForumAccountAdapter"
DEFAULT_FROM_EMAIL = "noreply@clashbang.forum"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django.security.csrf": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}
