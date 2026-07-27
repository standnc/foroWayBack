"""
Tests de escritura: crear hilo y responder.

La suite anterior no tenía ni un solo client.post, y las factories rellenaban
`creado` a mano, así que el IntegrityError de Hilo.creado / Post.creado
(NOT NULL sin default) era invisible. Estos tests recorren el camino real
del usuario, que es donde reventaba.
"""

import pytest
from django.urls import reverse

from forum.models import Categoria, Hilo, Post
from forum.tests.conftest import CategoriaFactory, HiloFactory, PostFactory


@pytest.fixture
def categoria_nueva(db):
    """Categoría del foro activo: es donde se puede publicar."""
    return CategoriaFactory(es_clashbang=True)


class TestCrearHilo:
    def test_crear_hilo_funciona(self, auth_client, categoria_nueva, verified_user):
        r = auth_client.post(
            reverse("forum:crear_hilo"),
            {
                "titulo": "Mi primer hilo en ClashBang",
                "categoria": categoria_nueva.pk,
                "contenido_apertura": "Hola a todos, cuánto tiempo.",
            },
        )
        assert r.status_code == 302, "crear un hilo debe redirigir al hilo creado"

        hilo = Hilo.objects.get(titulo="Mi primer hilo en ClashBang")
        assert hilo.autor == verified_user
        assert hilo.creado is not None, "el bug original: creado se quedaba en None"
        assert hilo.es_historico is False, "un hilo nuevo no es del archivo histórico"
        assert hilo.slug, "el slug no puede quedar vacío"
        assert r.url == reverse("forum:hilo", kwargs={"pk": hilo.pk})

    def test_crear_hilo_genera_el_post_de_apertura(self, auth_client, categoria_nueva):
        auth_client.post(
            reverse("forum:crear_hilo"),
            {
                "titulo": "Hilo con apertura",
                "categoria": categoria_nueva.pk,
                "contenido_apertura": "Cuerpo del primer mensaje.",
            },
        )
        hilo = Hilo.objects.get(titulo="Hilo con apertura")
        apertura = hilo.posts.get(orden=0)
        assert apertura.contenido == "Cuerpo del primer mensaje."
        assert apertura.creado is not None
        assert apertura.es_historico is False

    def test_anonimo_no_crea_hilo(self, client, categoria_nueva):
        r = client.post(
            reverse("forum:crear_hilo"),
            {"titulo": "No debería", "categoria": categoria_nueva.pk, "contenido_apertura": "x"},
        )
        assert r.status_code == 302
        assert Hilo.objects.filter(titulo="No debería").count() == 0

    def test_no_verificado_no_crea_hilo(self, client, user, categoria_nueva):
        client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        r = client.post(
            reverse("forum:crear_hilo"),
            {"titulo": "Tampoco", "categoria": categoria_nueva.pk, "contenido_apertura": "x"},
        )
        assert r.url == reverse("forum:verify_waiting")
        assert Hilo.objects.filter(titulo="Tampoco").count() == 0

    def test_titulo_corto_no_pasa(self, auth_client, categoria_nueva):
        r = auth_client.post(
            reverse("forum:crear_hilo"),
            {"titulo": "ab", "categoria": categoria_nueva.pk, "contenido_apertura": "x"},
        )
        assert r.status_code == 200  # vuelve al formulario con errores
        assert Hilo.objects.count() == 0


class TestResponder:
    @pytest.fixture
    def hilo_abierto(self, db, categoria_nueva, verified_user):
        h = HiloFactory(categoria=categoria_nueva, autor=verified_user, es_historico=False)
        PostFactory(hilo=h, autor=verified_user, orden=0, es_historico=False)
        return h

    def test_responder_funciona(self, auth_client, hilo_abierto, verified_user):
        r = auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk}),
            {"contenido": "Mi respuesta al hilo."},
        )
        assert r.status_code == 302
        respuesta = Post.objects.get(contenido="Mi respuesta al hilo.")
        assert respuesta.autor == verified_user
        assert respuesta.creado is not None, "el bug original: creado se quedaba en None"
        assert respuesta.hilo == hilo_abierto

    def test_orden_es_max_mas_uno_no_un_contador(self, auth_client, hilo_abierto, verified_user):
        """El bug A2: se usaba Count("orden") en vez de Max("orden").

        Con un hueco en la secuencia, contar filas devuelve un orden ya usado.
        """
        PostFactory(hilo=hilo_abierto, autor=verified_user, orden=7, es_historico=False)
        # Ahora hay 2 posts (orden 0 y 7). Count daría 2; Max+1 debe dar 8.
        auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk}),
            {"contenido": "Respuesta tras el hueco."},
        )
        nueva = Post.objects.get(contenido="Respuesta tras el hueco.")
        assert nueva.orden == 8

    def test_ordenes_no_se_repiten(self, auth_client, hilo_abierto):
        for i in range(3):
            auth_client.post(
                reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk}),
                {"contenido": f"Respuesta {i}"},
            )
        ordenes = list(hilo_abierto.posts.values_list("orden", flat=True))
        assert len(ordenes) == len(set(ordenes)), f"órdenes duplicados: {ordenes}"

    def test_respuesta_actualiza_ultimo_post(self, auth_client, hilo_abierto):
        auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk}),
            {"contenido": "Marca el hilo como reciente."},
        )
        hilo_abierto.refresh_from_db()
        nueva = Post.objects.get(contenido="Marca el hilo como reciente.")
        assert hilo_abierto.ultimo_post == nueva.creado

    def test_respuesta_vacia_no_se_guarda(self, auth_client, hilo_abierto):
        antes = hilo_abierto.posts.count()
        r = auth_client.post(
            reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk}),
            {"contenido": "   "},
        )
        assert r.status_code == 200
        assert hilo_abierto.posts.count() == antes


class TestDefaultsDelModelo:
    """El default de `creado` debe funcionar sin que nadie lo rellene."""

    def test_hilo_sin_creado_explicito(self, db, categoria_nueva):
        h = Hilo.objects.create(categoria=categoria_nueva, titulo="Sin fecha", slug="sin-fecha")
        assert h.creado is not None

    def test_post_sin_creado_explicito(self, db, categoria_nueva):
        h = Hilo.objects.create(categoria=categoria_nueva, titulo="H", slug="h")
        p = Post.objects.create(hilo=h, contenido="texto")
        assert p.creado is not None

    def test_migrar_sqlite_puede_seguir_escribiendo_fechas_viejas(self, db, categoria_nueva):
        """El default no debe pisar las fechas del scrape (por eso no es auto_now_add)."""
        from datetime import UTC, datetime

        vieja = datetime(2009, 5, 17, 12, 0, tzinfo=UTC)
        h = Hilo.objects.create(
            categoria=categoria_nueva, titulo="Del scrape", slug="del-scrape", creado=vieja
        )
        assert h.creado == vieja


class TestPerfil404:
    def test_perfil_inexistente_da_404(self, client, db):
        r = client.get(reverse("forum:perfil", kwargs={"username": "nadie-con-este-nombre"}))
        assert r.status_code == 404

    def test_perfil_existente_da_200(self, client, user):
        r = client.get(reverse("forum:perfil", kwargs={"username": user.username}))
        assert r.status_code == 200


class TestUsernameUnico:
    """A7: create_user dejaba username="" y el segundo usuario chocaba."""

    def test_dos_usuarios_sin_username_explicito(self, db):
        from accounts.models import User

        u1 = User.objects.create_user(email="pedro@ejemplo.com", password="x")
        u2 = User.objects.create_user(email="pedro@otrodominio.com", password="x")
        assert u1.username and u2.username
        assert u1.username != u2.username

    def test_email_se_guarda_en_minusculas(self, db):
        """normalize_email solo baja el dominio y dejaba la cuenta inaccesible."""
        from accounts.models import User

        u = User.objects.create_user(email="Pedro@Ejemplo.com", password="x")
        assert u.email == "pedro@ejemplo.com"

    def test_login_tras_registrarse_con_mayusculas(self, db, client):
        """Con la parte local en mayúsculas no se podía entrar ni con el email exacto."""
        from accounts.models import User

        User.objects.create_user(email="Pedro@Ejemplo.com", password="clave-larga-123")
        r = client.post(
            reverse("account_login"),
            {"login": "pedro@ejemplo.com", "password": "clave-larga-123"},
        )
        assert r.status_code == 302, "un login válido redirige"
        assert r.wsgi_request.user.is_authenticated


class TestResolverReportSinDuracion:
    """A5: banear con el selector de duración vacío daba un 500 (int(""))."""

    def test_banear_sin_duracion_devuelve_formulario_no_500(self, staff_client, report):
        r = staff_client.post(
            reverse("forum:resolver_report", kwargs={"pk": report.pk}),
            {"accion": "banear", "nota": "spam", "duracion_ban": ""},
        )
        assert r.status_code == 200
        assert "duracion_ban" in r.context["form"].errors

    def test_banear_con_duracion_funciona(self, staff_client, report):
        from forum.models import Ban

        r = staff_client.post(
            reverse("forum:resolver_report", kwargs={"pk": report.pk}),
            {"accion": "banear", "nota": "spam", "duracion_ban": "7"},
        )
        assert r.status_code == 302
        assert Ban.objects.filter(usuario=report.post.autor, activo=True).exists()


class TestAdminLogs:
    """A4: /admin/logs/ lo capturaba el catch-all del admin. A6: ?max=abc daba 500."""

    def test_ruta_resuelve_a_la_vista_propia(self):
        from django.urls import resolve

        from forum.admin_logs import log_view

        assert resolve("/admin/logs/").func == log_view

    def test_max_no_numerico_no_revienta(self, staff_client):
        r = staff_client.get("/admin/logs/", {"max": "abc"})
        assert r.status_code == 200

    def test_no_staff_no_entra(self, client, verified_user):
        client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
        r = client.get("/admin/logs/")
        assert r.status_code == 302


def test_categoria_factory_disponible():
    """Guardarraíl: si esto falla es que se movieron las factories."""
    assert Categoria is not None
