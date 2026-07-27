"""Settings para la suite de tests.

Fuerza SQLite en memoria y desactiva el hardening de prod para que los tests
no dependan de PostgreSQL ni del .env de la máquina.
"""
from .settings import *  # noqa: F403

# El hardening de prod (settings.py) se activa con DEBUG=False y rompe el test client.
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# BD aislada: nada de tocar la sqlite local ni PostgreSQL.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Argon2 es deliberadamente lento; en tests no aporta nada.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# axes bloquearía los tests de login por intentos repetidos desde la misma IP.
AXES_ENABLED = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
ACCOUNT_EMAIL_VERIFICATION = "none"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
