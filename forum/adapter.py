import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class ForumAccountAdapter(DefaultAccountAdapter):
    def generate_unique_username(self, email):
        base = email.split("@")[0][:30]
        username = base
        while User.objects.filter(username=username).exists():
            import random
            username = f"{base}_{random.randint(1000, 9999)}"
        return username

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.username:
            user.username = self.generate_unique_username(user.email)
        if commit:
            user.save()
        return user


class ForumSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Evita colisiones de email entre OAuth y registro tradicional.
    Si el email del proveedor OAuth ya existe en BD, vincula la cuenta social
    al usuario existente en lugar de crear un duplicado.
    """
    def pre_social_login(self, request, sociallogin):
        email = sociallogin.account.extra_data.get("email", "").lower().strip()
        if not email:
            return

        # Si ya hay un user autenticado, no intervenimos
        if request.user.is_authenticated:
            return

        # El social login ya está vinculado a un usuario existente → no hacer nada
        if sociallogin.is_existing:
            return

        try:
            existing_user = User.objects.get(email=email)
        except User.DoesNotExist:
            return

        logger.info(
            "Vinculando cuenta social existente para email=%s | provider=%s",
            email,
            sociallogin.account.provider,
        )
        sociallogin.connect(request, existing_user)
