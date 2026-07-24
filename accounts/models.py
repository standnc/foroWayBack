from django.contrib.auth.models import AbstractUser
from django.db import models
from .managers import CustomUserManager


class User(AbstractUser):
    """
    Custom User model con email como identificador principal.
    Los usuarios del scrape histórico NO tienen cuenta aquí — se muestran como texto plano.
    """
    email = models.EmailField(unique=True, verbose_name="email")
    bio = models.TextField(blank=True, max_length=500, verbose_name="biografía")
    firma = models.CharField(max_length=300, blank=True, verbose_name="firma")
    avatar_url = models.URLField(blank=True, verbose_name="avatar URL")
    is_verified = models.BooleanField(default=False, verbose_name="verificado")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # solo email + password para createsuperuser

    objects = CustomUserManager()

    class Meta:
        db_table = "users"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-date_joined"]

    def __str__(self):
        return self.email
