import logging
import math
from contextlib import contextmanager

from allauth.account.signals import email_confirmed
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Categoria, Hilo, Post, UserProfile

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


# ─── Contadores denormalizados ──────────────────────────────
#
# Categoria.num_hilos/num_posts e Hilo.num_posts se muestran al usuario en
# categoria_list.html. El comentario del modelo decía "actualizados por
# señales" y no existía ninguna: solo el comando one-shot, así que derivaban
# en cuanto alguien publicaba.

@contextmanager
def contadores_en_pausa():
    """Desconecta las señales de contadores durante una importación masiva.

    migrar_sqlite crea miles de filas: mantener los contadores fila a fila son
    dos queries extra por post. El comando recalcula todo al terminar.
    """
    receptores = [
        (post_save, refrescar_contadores_por_post, Post),
        (post_delete, refrescar_contadores_por_post, Post),
        (post_save, refrescar_contadores_por_hilo, Hilo),
        (post_delete, refrescar_contadores_por_hilo, Hilo),
    ]
    for senal, receptor, modelo in receptores:
        senal.disconnect(receptor, sender=modelo)
    try:
        yield
    finally:
        for senal, receptor, modelo in receptores:
            senal.connect(receptor, sender=modelo)


def _refrescar_contadores_de_hilo(hilo):
    Hilo.objects.filter(pk=hilo.pk).update(num_posts=hilo.posts.count())


def _refrescar_contadores_de_categoria(categoria):
    Categoria.objects.filter(pk=categoria.pk).update(
        num_hilos=categoria.hilos.count(),
        num_posts=Post.objects.filter(hilo__categoria=categoria).count(),
    )


@receiver([post_save, post_delete], sender=Post)
def refrescar_contadores_por_post(sender, instance, **kwargs):
    hilo = instance.hilo
    _refrescar_contadores_de_hilo(hilo)
    _refrescar_contadores_de_categoria(hilo.categoria)


@receiver([post_save, post_delete], sender=Hilo)
def refrescar_contadores_por_hilo(sender, instance, **kwargs):
    _refrescar_contadores_de_categoria(instance.categoria)


@receiver(email_confirmed)
def marcar_verificado_tras_confirmar(sender, request, email_address, **kwargs):
    """Cuando allauth confirma un email, sincroniza User.is_verified."""
    user = email_address.user
    if not user.is_verified:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        logger.info("Email confirmado → User.is_verified=True para %s", user.email)
