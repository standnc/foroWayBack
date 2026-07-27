"""Login y registro inline vía HTMX, sobre los formularios de allauth.

Cuidado con ImmediateHttpResponse: allauth la usa como control de flujo, no
como error. Es lo que devuelve la pantalla de "confirma tu email" con
ACCOUNT_EMAIL_VERIFICATION=mandatory y también los cortes por rate limit.
Tragársela y responder con un HX-Redirect a "/" equivale a decirle al usuario
que ha entrado cuando no lo ha hecho, y anula la verificación obligatoria.
"""

import logging

from allauth.account.forms import LoginForm, SignupForm
from allauth.account.internal.flows.signup import complete_signup
from allauth.core.exceptions import ImmediateHttpResponse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View

# "forum", no "foro": el logger tiene que existir en settings.LOGGING o los
# errores de esta vista no se escriben en ninguna parte.
logger = logging.getLogger("forum")


def _hx_redirect(url="/"):
    """Redirección del lado de HTMX (el navegador la ejecuta al recibirla)."""
    response = HttpResponse(status=204)
    response["HX-Redirect"] = url
    return response


def _destino_de(respuesta):
    """URL a la que apunta una respuesta de allauth, si es una redirección."""
    return respuesta.headers.get("Location") if respuesta.status_code in (301, 302, 303, 307, 308) else None


def _traducir_interrupcion(e, contexto):
    """Convierte una ImmediateHttpResponse de allauth en algo que HTMX entienda."""
    destino = _destino_de(e.response)
    logger.info("%s: allauth interrumpe el flujo → %s", contexto, destino or "respuesta propia")
    return _hx_redirect(destino) if destino else e.response


class _InlineAuthView(View):
    """Base común: POST procesa el formulario, GET devuelve a la portada."""

    template_name = ""

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect("/")

    def _render_form(self, request, form, status=422):
        return render(request, self.template_name, {"form": form}, status=status)

    def _destino_tras_exito(self, request):
        """Adónde mandar al usuario cuando el flujo termina bien."""
        return "/"


class InlineLoginView(_InlineAuthView):
    template_name = "forum/_login_form.html"

    def post(self, request, *args, **kwargs):
        form = LoginForm(request=request, data=request.POST, files=request.FILES)
        if not form.is_valid():
            return self._render_form(request, form)

        try:
            form.login(request)
        except ImmediateHttpResponse as e:
            # allauth ha decidido a dónde va el usuario (confirmar email,
            # rate limit, 2FA...). Se respeta su destino en vez de fingir éxito.
            return _traducir_interrupcion(e, "InlineLogin")
        except Exception:
            logger.exception("InlineLogin: error inesperado")
            form.add_error(None, "No hemos podido iniciar sesión. Inténtalo de nuevo.")
            return self._render_form(request, form, status=500)

        if not request.user.is_authenticated:
            # form.login() no dejó sesión: no se anuncia un éxito que no existe.
            logger.warning("InlineLogin: form.login() no autenticó al usuario")
            form.add_error(None, "No hemos podido iniciar sesión. Inténtalo de nuevo.")
            return self._render_form(request, form)

        return _hx_redirect(self._destino_tras_exito(request))


class InlineSignupView(_InlineAuthView):
    template_name = "forum/_signup_form.html"

    def post(self, request, *args, **kwargs):
        form = SignupForm(request=request, data=request.POST, files=request.FILES)
        if not form.is_valid():
            return self._render_form(request, form)

        try:
            user = form.save(request)
            complete_signup(request, user=user, redirect_url="/", by_passkey=False)
        except ImmediateHttpResponse as e:
            return _traducir_interrupcion(e, "InlineSignup")
        except Exception:
            logger.exception("InlineSignup: error inesperado")
            form.add_error(None, "No hemos podido completar el registro. Inténtalo de nuevo.")
            return self._render_form(request, form, status=500)

        # Con ACCOUNT_EMAIL_VERIFICATION=mandatory el registro NO deja sesión:
        # el usuario debe confirmar el email primero. Se le lleva al aviso de
        # allauth (forum:verify_waiting exige login, aquí aún no lo hay) en vez
        # de a la portada como si ya estuviera dentro.
        if not request.user.is_authenticated:
            return _hx_redirect(reverse("account_email_verification_sent"))

        return _hx_redirect(self._destino_tras_exito(request))
