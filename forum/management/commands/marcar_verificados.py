from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = (
        "One-shot: pone is_verified=True a los usuarios cuyo email ya está "
        "verificado en allauth (EmailAddress.verified=True)."
    )

    def handle(self, *args, **options):
        emails_verificados = EmailAddress.objects.filter(verified=True).values_list("email", flat=True)
        actualizados = User.objects.filter(email__in=emails_verificados, is_verified=False).update(is_verified=True)
        self.stdout.write(self.style.SUCCESS(f"is_verified=True para {actualizados} usuarios"))
