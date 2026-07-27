"""Aplicación efectiva de los baneos.

Hasta ahora Ban se creaba, se auditaba en ModerationLog y se contaba en el
panel, pero ningún punto del código lo consultaba: un usuario baneado seguía
entrando y publicando. Este middleware es el que lo hace valer.
"""

import logging

from django.contrib.auth import logout
from django.shortcuts import render
from django.utils import timezone

from .models import Ban, UserProfile

logger = logging.getLogger("forum")

# Rutas accesibles aun estando baneado: cerrar sesión y los estáticos/medios.
# Sin esto el usuario quedaría atrapado sin poder ni desloguearse.
RUTAS_PERMITIDAS = ("/accounts/logout/", "/static/", "/media/", "/admin/jsi18n/")


class BanEnforcementMiddleware:
    """Corta el paso a los usuarios con un baneo activo.

    - Caduca los baneos temporales vencidos (activo=False) al vuelo.
    - Cierra la sesión del baneado y le muestra el motivo y la fecha de fin.
    - Mantiene UserProfile.estado_usuario sincronizado para el badge "Game Over".
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if usuario is None or not usuario.is_authenticated:
            return self.get_response(request)

        if request.path.startswith(RUTAS_PERMITIDAS):
            return self.get_response(request)

        ban = self._ban_vigente(usuario)
        if ban is None:
            return self.get_response(request)

        logger.info("Acceso bloqueado por baneo: usuario=%s ban=%s", usuario.pk, ban.pk)
        self._marcar_perfil(usuario, "baneado")
        logout(request)
        return render(request, "forum/baneado.html", {"ban": ban}, status=403)

    def _ban_vigente(self, usuario):
        """Devuelve el baneo que sigue en vigor, caducando los que ya expiraron."""
        ahora = timezone.now()
        activos = Ban.objects.filter(usuario=usuario, activo=True)

        vencidos = [b for b in activos if b.expira is not None and b.expira <= ahora]
        if vencidos:
            Ban.objects.filter(pk__in=[b.pk for b in vencidos]).update(
                activo=False, levantado=ahora
            )
            logger.info("Baneos caducados para usuario=%s: %s", usuario.pk, [b.pk for b in vencidos])

        vigentes = [b for b in activos if b.expira is None or b.expira > ahora]
        if not vigentes:
            if vencidos:
                # Se le acaba de levantar el último baneo: deja de ser "Game Over".
                self._marcar_perfil(usuario, "activo")
            return None

        # El permanente manda; si no, el que más tarde expire.
        permanentes = [b for b in vigentes if b.expira is None]
        return permanentes[0] if permanentes else max(vigentes, key=lambda b: b.expira)

    @staticmethod
    def _marcar_perfil(usuario, estado):
        perfil = UserProfile.objects.filter(user=usuario).first()
        if perfil is not None and perfil.estado_usuario != estado:
            perfil.estado_usuario = estado
            perfil.save(update_fields=["estado_usuario"])
