import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class ForumAccountAdapter(DefaultAccountAdapter):
    """Rellena el username, que allauth no gestiona.

    ACCOUNT_USER_MODEL_USERNAME_FIELD = None, así que allauth ignora el campo,
    pero sigue siendo unique en AbstractUser y forum:perfil lo usa en la URL.
    La generación vive en CustomUserManager: no se sobreescribe el
    generate_unique_username de allauth, cuya firma es (txts, regex).
    """

    def clean_email(self, email):
        # A juego con CustomUserManager.create_user: el email se guarda siempre
        # en minúsculas para que la cuenta sea accesible y no haya duplicados
        # que solo difieran en mayúsculas.
        return super().clean_email(email).lower()

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if user.email:
            user.email = user.email.lower()
        if not user.username:
            user.username = User.objects.generate_unique_username(user.email)
        if commit:
            user.save()
        return user


def _email_verificado_por_el_provider(sociallogin):
    """¿El proveedor OAuth afirma haber verificado este email?

    Solo cuenta la dirección que coincide con la de la cuenta social; que el
    usuario tenga otra dirección verificada no autoriza nada sobre esta.
    """
    email_cuenta = (sociallogin.account.extra_data.get("email") or "").lower().strip()
    for direccion in getattr(sociallogin, "email_addresses", None) or []:
        if direccion.email.lower().strip() == email_cuenta:
            return bool(direccion.verified)
    return False


class ForumSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Evita colisiones de email entre OAuth y registro tradicional.
    Si el email del proveedor OAuth ya existe en BD **y el proveedor lo ha
    verificado**, vincula la cuenta social al usuario existente en lugar de
    crear un duplicado. También marca User.is_verified=True (D5).
    """

    def pre_social_login(self, request, sociallogin):
        email = (sociallogin.account.extra_data.get("email") or "").lower().strip()
        if not email:
            return

        # Si ya hay un user autenticado, no intervenimos
        if request.user.is_authenticated:
            return

        # El social login ya está vinculado a un usuario existente → no hacer nada
        if sociallogin.is_existing:
            return

        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # Sin esta comprobación, cualquiera que cree una cuenta en un proveedor
        # que no verifica el email (GitHub, Discord) usando la dirección de la
        # víctima se queda con su cuenta del foro. Es el motivo por el que
        # allauth no vincula por email automáticamente.
        if not _email_verificado_por_el_provider(sociallogin):
            logger.warning(
                "Vinculación automática rechazada: %s no ha verificado el email %s "
                "que ya pertenece al usuario id=%s. Se pedirá confirmación.",
                sociallogin.account.provider, email, existing_user.pk,
            )
            return

        logger.info(
            "Vinculando cuenta social existente para email=%s | provider=%s",
            email,
            sociallogin.account.provider,
        )
        sociallogin.connect(request, existing_user)

    def save_user(self, request, sociallogin, form=None):
        """Marca is_verified=True si el provider entrega el email verificado (D5)."""
        user = super().save_user(request, sociallogin, form)

        if _email_verificado_por_el_provider(sociallogin) and not user.is_verified:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            logger.info("OAuth (provider=%s) → User.is_verified=True para %s",
                        sociallogin.account.provider, user.email)

        return user
