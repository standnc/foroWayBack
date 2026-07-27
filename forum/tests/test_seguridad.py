"""
Tests de los agujeros de seguridad de la Fase 2.

Cada clase corresponde a un fallo concreto que existía y era explotable.
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.urls import reverse
from django.utils import timezone

from forum.models import Ban, Hilo, Post, UserProfile
from forum.tests.conftest import CategoriaFactory, HiloFactory, PostFactory


@pytest.fixture
def categoria_activa(db):
    return CategoriaFactory(es_clashbang=True)


@pytest.fixture
def categoria_historica(db):
    return CategoriaFactory(es_clashbang=False)


# ─── B1: vinculación automática de cuentas OAuth ──────────

class _CuentaFalsa:
    def __init__(self, email, provider="github"):
        self.extra_data = {"email": email}
        self.provider = provider


def _sociallogin(email, verificado, provider="github"):
    """Imita lo justo de un SocialLogin para el adapter."""
    return SimpleNamespace(
        account=_CuentaFalsa(email, provider),
        email_addresses=[SimpleNamespace(email=email, verified=verificado)],
        is_existing=False,
        connect=lambda request, user: setattr(_sociallogin, "conectado", user),
    )


class TestVinculacionOAuth:
    """Vincular por email sin comprobar la verificación = takeover de cuenta."""

    def _adapter(self):
        from forum.adapter import ForumSocialAccountAdapter

        return ForumSocialAccountAdapter()

    def test_no_vincula_si_el_provider_no_verifico_el_email(self, db, user, rf):
        """El ataque: registrarse en GitHub con el email de la víctima."""
        conectados = []
        sl = _sociallogin(user.email, verificado=False)
        sl.connect = lambda request, u: conectados.append(u)

        request = rf.get("/")
        request.user = SimpleNamespace(is_authenticated=False)
        self._adapter().pre_social_login(request, sl)

        assert conectados == [], "no debe vincularse a la cuenta existente"

    def test_vincula_si_el_provider_verifico_el_email(self, db, user, rf):
        conectados = []
        sl = _sociallogin(user.email, verificado=True, provider="google")
        sl.connect = lambda request, u: conectados.append(u)

        request = rf.get("/")
        request.user = SimpleNamespace(is_authenticated=False)
        self._adapter().pre_social_login(request, sl)

        assert conectados == [user]

    def test_no_vincula_si_la_direccion_verificada_es_otra(self, db, user, rf):
        """Tener otra dirección verificada no autoriza nada sobre esta."""
        conectados = []
        sl = _sociallogin(user.email, verificado=True)
        sl.email_addresses = [SimpleNamespace(email="otra@dominio.com", verified=True)]
        sl.connect = lambda request, u: conectados.append(u)

        request = rf.get("/")
        request.user = SimpleNamespace(is_authenticated=False)
        self._adapter().pre_social_login(request, sl)

        assert conectados == []


# ─── B3: enforcement de baneos ────────────────────────────

class TestBanEnforcement:
    def test_baneado_no_navega(self, client, verified_user, moderator, categoria_activa):
        Ban.objects.create(
            usuario=verified_user, moderador=moderator,
            motivo="Spam masivo", tipo="permanente", activo=True,
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        r = client.get(reverse("forum:index"))
        assert r.status_code == 403
        assert "Spam masivo" in r.content.decode()

    def test_baneado_pierde_la_sesion(self, client, verified_user, moderator):
        Ban.objects.create(
            usuario=verified_user, moderador=moderator,
            motivo="x", tipo="permanente", activo=True,
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        client.get(reverse("forum:index"))
        r = client.get(reverse("forum:index"))
        assert not r.wsgi_request.user.is_authenticated

    def test_baneado_no_publica(self, client, verified_user, moderator, categoria_activa):
        hilo = HiloFactory(categoria=categoria_activa, autor=verified_user, es_historico=False)
        Ban.objects.create(
            usuario=verified_user, moderador=moderator,
            motivo="x", tipo="permanente", activo=True,
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        r = client.post(reverse("forum:hilo", kwargs={"pk": hilo.pk}), {"contenido": "hola"})
        assert r.status_code == 403
        assert not Post.objects.filter(contenido="hola").exists()

    def test_ban_temporal_vencido_deja_pasar_y_se_marca_inactivo(self, client, verified_user, moderator):
        ban = Ban.objects.create(
            usuario=verified_user, moderador=moderator, motivo="x",
            tipo="temporal", activo=True, expira=timezone.now() - timedelta(days=1),
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        r = client.get(reverse("forum:index"))
        assert r.status_code == 200
        ban.refresh_from_db()
        assert ban.activo is False
        assert ban.levantado is not None

    def test_ban_temporal_vigente_bloquea(self, client, verified_user, moderator):
        Ban.objects.create(
            usuario=verified_user, moderador=moderator, motivo="x",
            tipo="temporal", activo=True, expira=timezone.now() + timedelta(days=3),
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        assert client.get(reverse("forum:index")).status_code == 403

    def test_ban_marca_el_perfil_como_game_over(self, client, verified_user, moderator):
        perfil = UserProfile.objects.create(user=verified_user)
        Ban.objects.create(
            usuario=verified_user, moderador=moderator, motivo="x",
            tipo="permanente", activo=True,
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        client.get(reverse("forum:index"))
        perfil.refresh_from_db()
        assert perfil.estado_usuario == "baneado"
        assert perfil.is_game_over

    def test_el_baneado_puede_cerrar_sesion(self, client, verified_user, moderator):
        """Sin la allowlist quedaría atrapado sin poder desloguearse."""
        Ban.objects.create(
            usuario=verified_user, moderador=moderator, motivo="x",
            tipo="permanente", activo=True,
        )
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        assert client.get("/accounts/logout/").status_code in (200, 302)

    def test_usuario_sin_ban_no_se_entera(self, client, verified_user):
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        assert client.get(reverse("forum:index")).status_code == 200

    def test_anonimo_no_se_entera(self, client, db):
        assert client.get(reverse("forum:index")).status_code == 200


# ─── B6: fuga de emails ───────────────────────────────────

class TestEmailsNoPublicos:
    def test_el_perfil_no_muestra_el_email(self, client, db):
        from accounts.models import User

        u = User.objects.create_user(email="privado@ejemplo.com", password="x")
        assert not u.display_name, "el caso interesante es sin display_name"
        r = client.get(reverse("forum:perfil", kwargs={"username": u.username}))
        assert r.status_code == 200
        assert "privado@ejemplo.com" not in r.content.decode()

    def test_el_hilo_no_muestra_el_email_del_autor(self, auth_client, categoria_activa, db):
        from accounts.models import User

        autor = User.objects.create_user(email="autor@ejemplo.com", password="x")
        hilo = HiloFactory(categoria=categoria_activa, autor=autor)
        PostFactory(hilo=hilo, autor=autor, orden=0)
        r = auth_client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk}))
        assert "autor@ejemplo.com" not in r.content.decode()

    def test_public_name_nunca_es_el_email(self, db):
        from accounts.models import User

        u = User.objects.create_user(email="alguien@ejemplo.com", password="x")
        assert "@" not in u.public_name
        u.display_name = "Pedro"
        assert u.public_name == "Pedro"


# ─── B7: escritura en el archivo histórico ────────────────

class TestArchivoHistorico:
    def test_no_se_puede_responder_a_un_hilo_historico(self, auth_client, categoria_historica):
        hilo = HiloFactory(categoria=categoria_historica, es_historico=True)
        r = auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo.pk}), {"contenido": "respuesta nueva"}
        )
        assert r.status_code == 403
        assert not Post.objects.filter(contenido="respuesta nueva").exists()

    def test_no_se_puede_responder_a_un_hilo_cerrado(self, auth_client, categoria_activa):
        hilo = HiloFactory(categoria=categoria_activa, es_historico=False, cerrado=True)
        r = auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo.pk}), {"contenido": "a ver"}
        )
        assert r.status_code == 403

    def test_el_formulario_no_se_muestra_en_hilos_historicos(self, auth_client, categoria_historica):
        hilo = HiloFactory(categoria=categoria_historica, es_historico=True)
        cuerpo = auth_client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk})).content.decode()
        assert "solo lectura" in cuerpo.lower()
        assert "Publicar respuesta" not in cuerpo

    def test_no_se_puede_crear_un_hilo_en_una_categoria_historica(
        self, auth_client, categoria_historica
    ):
        r = auth_client.post(
            reverse("forum:crear_hilo"),
            {
                "titulo": "Colándome en el archivo",
                "categoria": categoria_historica.pk,
                "contenido_apertura": "no debería poder",
            },
        )
        assert r.status_code == 200, "vuelve al formulario con error de categoría"
        assert not Hilo.objects.filter(titulo="Colándome en el archivo").exists()

    def test_si_se_puede_crear_en_una_categoria_activa(self, auth_client, categoria_activa):
        r = auth_client.post(
            reverse("forum:crear_hilo"),
            {
                "titulo": "Hilo legítimo del foro nuevo",
                "categoria": categoria_activa.pk,
                "contenido_apertura": "hola",
            },
        )
        assert r.status_code == 302
        assert Hilo.objects.filter(titulo="Hilo legítimo del foro nuevo").exists()


# ─── B4: SECRET_KEY ───────────────────────────────────────

class TestSecretKey:
    def test_no_arranca_en_produccion_sin_secret_key(self, monkeypatch):
        """Con DEBUG=False y sin SECRET_KEY los settings deben negarse a cargar."""
        import importlib

        from django.core.exceptions import ImproperlyConfigured

        monkeypatch.setenv("DEBUG", "False")
        monkeypatch.setenv("SECRET_KEY", "")
        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

        import config.settings as s

        with pytest.raises(ImproperlyConfigured):
            importlib.reload(s)

        # Deja el módulo como estaba para el resto de la suite.
        monkeypatch.undo()
        importlib.reload(s)
