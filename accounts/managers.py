from django.contrib.auth.models import BaseUserManager
from django.utils.crypto import get_random_string
from django.utils.text import slugify


class CustomUserManager(BaseUserManager):
    def generate_unique_username(self, email):
        """Deriva un username libre a partir del email.

        El modelo hereda `username` de AbstractUser con unique=True, pero
        USERNAME_FIELD es el email y REQUIRED_FIELDS está vacío: sin esto,
        create_user deja username="" y el segundo usuario choca contra el
        índice único. Además forum:perfil usa el username en la URL.
        """
        base = slugify(email.split("@")[0])[:30] or "usuario"
        username = base
        for i in range(1, 100):
            if not self.filter(username=username).exists():
                return username
            sufijo = f"-{i}"
            username = f"{base[:30 - len(sufijo)]}{sufijo}"
        # Salida de emergencia: sufijo aleatorio.
        return f"{base[:23]}-{get_random_string(6)}"

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        # normalize_email solo baja el dominio. Con la parte local en mayúsculas
        # la cuenta quedaba inaccesible (allauth normaliza el login introducido
        # y ModelBackend busca por coincidencia exacta) y además "Pedro@x.com"
        # y "pedro@x.com" convivían como dos cuentas pese a unique=True.
        email = self.normalize_email(email).lower()
        extra_fields.setdefault("username", self.generate_unique_username(email))
        if not extra_fields.get("username"):
            extra_fields["username"] = self.generate_unique_username(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser debe tener is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser debe tener is_superuser=True")
        return self.create_user(email, password, **extra_fields)
