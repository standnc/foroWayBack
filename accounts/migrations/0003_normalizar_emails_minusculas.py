"""Normaliza a minúsculas los emails ya guardados.

`BaseUserManager.normalize_email` solo baja el dominio, así que las cuentas
creadas con mayúsculas en la parte local quedaron inaccesibles: allauth
normaliza el login introducido y el backend busca por coincidencia exacta.

Las colisiones (dos cuentas que solo difieren en mayúsculas) NO se tocan: se
dejan como están y se listan por el logger para resolverlas a mano, porque
fusionarlas automáticamente implicaría decidir qué contenido sobrevive.
"""

import logging

from django.db import migrations

logger = logging.getLogger("accounts")


def normalizar(apps, schema_editor):
    User = apps.get_model("accounts", "User")

    existentes = set(User.objects.values_list("email", flat=True))
    for user in User.objects.exclude(email=""):
        bajado = user.email.lower()
        if bajado == user.email:
            continue
        if bajado in existentes:
            logger.warning(
                "Email no normalizado por colisión: %s choca con %s (user id=%s)",
                user.email, bajado, user.pk,
            )
            continue
        existentes.discard(user.email)
        existentes.add(bajado)
        user.email = bajado
        user.save(update_fields=["email"])

    # Misma operación sobre la tabla de allauth, que es la que consulta el login.
    try:
        EmailAddress = apps.get_model("account", "EmailAddress")
    except LookupError:
        return
    vistos = set(EmailAddress.objects.values_list("email", flat=True))
    for direccion in EmailAddress.objects.all():
        bajado = direccion.email.lower()
        if bajado == direccion.email or bajado in vistos:
            continue
        vistos.discard(direccion.email)
        vistos.add(bajado)
        direccion.email = bajado
        direccion.save(update_fields=["email"])


def revertir(apps, schema_editor):
    """Irreversible en la práctica: no se guarda el original. No-op."""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_display_name"),
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(normalizar, revertir),
    ]
