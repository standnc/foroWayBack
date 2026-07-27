import logging
import math

from allauth.account.signals import email_confirmed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post, UserProfile

logger = logging.getLogger(__name__)

def calcular_puntos(count):
    """Fórmula logarítmica: log2(1)=0pts, log2(100)≈60pts, log2(5000)=100pts"""
    return min(100, int(20 * math.log2(count + 1)))

def obtener_rango_por_mensajes(count):
    """Escala ClashBang/BoomBang confirmada"""
    if count >= 501:
        return 'Player from 09', '#f97316'      # orange-500
    elif count >= 251:
        return 'Leyenda', '#ef4444'              # red-500
    elif count >= 101:
        return 'Veterano', '#f59e0b'             # amber-500
    elif count >= 51:
        return 'BoomBanguer@', '#8b5cf6'         # violet-500
    elif count >= 21:
        return 'Clasher', '#06b6d4'              # cyan-500
    elif count >= 2:
        return 'BB Jr', '#22c55e'                # green-500
    else:
        return 'Hijo de Fr4n', '#94a3b8'         # slate-400

def actualizar_perfil(usuario):
    """Función reutilizable por señal y management command"""
    profile, created = UserProfile.objects.get_or_create(user=usuario)
    msg_count = profile.mensajes_count

    # Actualizar barra logarítmica
    profile.puntos_barra = calcular_puntos(msg_count)

    # Actualizar rango y color dinámicamente
    rango, color = obtener_rango_por_mensajes(msg_count)
    profile.rango_titulo = rango
    profile.color_rango = color

    profile.save(update_fields=['puntos_barra', 'rango_titulo', 'color_rango'])

@receiver(post_save, sender=Post)
def actualizar_perfil_al_postear(sender, instance, created, **kwargs):
    """Solo dispara para posts NUEVOS (no históricos)"""
    if not created:
        return
    if not instance.autor:  # posts históricos no tienen autor (usan autor_historico)
        return
    if instance.hilo.es_historico:  # el flag es_historico está en Hilo, no en Post
        return
    actualizar_perfil(instance.autor)


@receiver(email_confirmed)
def marcar_verificado_tras_confirmar(sender, request, email_address, **kwargs):
    """Cuando allauth confirma un email, sincroniza User.is_verified."""
    user = email_address.user
    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        logger.info("Email confirmado → User.is_verified=True para %s", user.email)
