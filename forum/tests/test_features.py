"""
Tests de la Fase 4: reportar, editar/borrar mensaje propio y rangos visibles.
"""

import pytest
from django.urls import reverse

from forum.models import ModerationLog, Post, Report, UserProfile
from forum.tests.conftest import CategoriaFactory, HiloFactory, PostFactory


@pytest.fixture
def categoria_activa(db):
    return CategoriaFactory(es_clashbang=True)


@pytest.fixture
def hilo_abierto(db, categoria_activa, verified_user):
    h = HiloFactory(categoria=categoria_activa, autor=verified_user, es_historico=False)
    PostFactory(hilo=h, autor=verified_user, orden=0, es_historico=False)
    return h


@pytest.fixture
def respuesta(db, hilo_abierto, verified_user):
    return PostFactory(hilo=hilo_abierto, autor=verified_user, orden=1, es_historico=False)


# ─── D1: reportar un post ─────────────────────────────────

class TestReportar:
    def test_se_puede_reportar(self, auth_client, respuesta, verified_user):
        r = auth_client.post(
            reverse("forum:reportar_post", kwargs={"pk": respuesta.pk}),
            {"tipo": "spam", "descripcion": "Publicidad encubierta"},
        )
        assert r.status_code == 302
        report = Report.objects.get()
        assert report.post == respuesta
        assert report.hilo == respuesta.hilo
        assert report.reportado_por == verified_user
        assert report.estado == "pendiente"

    def test_el_reporte_aparece_en_el_panel_de_moderacion(self, auth_client, staff_client, respuesta):
        auth_client.post(
            reverse("forum:reportar_post", kwargs={"pk": respuesta.pk}),
            {"tipo": "acoso", "descripcion": "x"},
        )
        r = staff_client.get(reverse("forum:moderation_panel"))
        assert r.status_code == 200
        assert Report.objects.count() == 1
        assert list(r.context["reportes_pendientes"])

    def test_anonimo_no_reporta(self, client, respuesta):
        r = client.post(
            reverse("forum:reportar_post", kwargs={"pk": respuesta.pk}),
            {"tipo": "spam", "descripcion": "x"},
        )
        assert r.status_code == 302
        assert Report.objects.count() == 0

    def test_el_boton_de_reportar_no_sale_en_tus_propios_mensajes(self, auth_client, respuesta):
        cuerpo = auth_client.get(reverse("forum:hilo", kwargs={"pk": respuesta.hilo.pk})).content.decode()
        assert reverse("forum:reportar_post", kwargs={"pk": respuesta.pk}) not in cuerpo


# ─── D2: editar y borrar el mensaje propio ────────────────

class TestEditarPost:
    def test_el_autor_edita_su_mensaje(self, auth_client, respuesta):
        r = auth_client.post(
            reverse("forum:editar_post", kwargs={"pk": respuesta.pk}),
            {"contenido": "Contenido corregido"},
        )
        assert r.status_code == 302
        respuesta.refresh_from_db()
        assert respuesta.contenido == "Contenido corregido"
        assert respuesta.editado is not None

    def test_otro_usuario_no_edita(self, client, respuesta, db):
        from accounts.models import User

        intruso = User.objects.create_user(email="intruso@x.com", password="x", is_verified=True)
        client.force_login(intruso, backend="django.contrib.auth.backends.ModelBackend")
        r = client.post(
            reverse("forum:editar_post", kwargs={"pk": respuesta.pk}),
            {"contenido": "secuestrado"},
        )
        assert r.status_code in (302, 403)
        respuesta.refresh_from_db()
        assert respuesta.contenido != "secuestrado"

    def test_el_staff_puede_editar_y_queda_en_el_log(self, staff_client, respuesta):
        r = staff_client.post(
            reverse("forum:editar_post", kwargs={"pk": respuesta.pk}),
            {"contenido": "Editado por moderación"},
        )
        assert r.status_code == 302
        respuesta.refresh_from_db()
        assert respuesta.contenido == "Editado por moderación"
        assert ModerationLog.objects.filter(accion="editar_post", target_post=respuesta).exists()

    def test_no_se_edita_el_archivo_historico(self, auth_client, categoria_activa, verified_user):
        historico = PostFactory(
            hilo=HiloFactory(categoria=categoria_activa), autor=verified_user, es_historico=True
        )
        r = auth_client.post(
            reverse("forum:editar_post", kwargs={"pk": historico.pk}), {"contenido": "no"}
        )
        assert r.status_code in (302, 403)

    def test_contenido_vacio_no_pasa(self, auth_client, respuesta):
        original = respuesta.contenido
        r = auth_client.post(
            reverse("forum:editar_post", kwargs={"pk": respuesta.pk}), {"contenido": "   "}
        )
        assert r.status_code == 200
        respuesta.refresh_from_db()
        assert respuesta.contenido == original


class TestBorrarPost:
    def test_el_autor_borra_su_respuesta(self, auth_client, respuesta):
        pk = respuesta.pk
        r = auth_client.post(reverse("forum:borrar_post", kwargs={"pk": pk}))
        assert r.status_code == 302
        assert not Post.objects.filter(pk=pk).exists()

    def test_no_se_borra_el_mensaje_que_abre_el_hilo(self, auth_client, hilo_abierto):
        apertura = hilo_abierto.posts.get(orden=0)
        r = auth_client.post(reverse("forum:borrar_post", kwargs={"pk": apertura.pk}))
        assert r.status_code == 403
        assert Post.objects.filter(pk=apertura.pk).exists()

    def test_otro_usuario_no_borra(self, client, respuesta, db):
        from accounts.models import User

        intruso = User.objects.create_user(email="otro@x.com", password="x", is_verified=True)
        client.force_login(intruso, backend="django.contrib.auth.backends.ModelBackend")
        r = client.post(reverse("forum:borrar_post", kwargs={"pk": respuesta.pk}))
        assert r.status_code in (302, 403)
        assert Post.objects.filter(pk=respuesta.pk).exists()

    def test_borrar_actualiza_los_contadores(self, auth_client, respuesta, categoria_activa):
        hilo = respuesta.hilo
        auth_client.post(reverse("forum:borrar_post", kwargs={"pk": respuesta.pk}))
        hilo.refresh_from_db()
        categoria_activa.refresh_from_db()
        assert hilo.num_posts == 1
        assert categoria_activa.num_posts == 1


# ─── D3: los rangos, visibles por fin ─────────────────────

class TestRangosVisibles:
    def test_el_hilo_muestra_el_rango_del_autor(self, auth_client, respuesta, verified_user):
        from forum.signals import actualizar_perfil

        actualizar_perfil(verified_user)
        cuerpo = auth_client.get(reverse("forum:hilo", kwargs={"pk": respuesta.hilo.pk})).content.decode()
        perfil = UserProfile.objects.get(user=verified_user)
        assert perfil.rango_titulo in cuerpo

    def test_el_perfil_muestra_rango_y_progreso(self, client, verified_user):
        from forum.signals import actualizar_perfil

        actualizar_perfil(verified_user)
        perfil = UserProfile.objects.get(user=verified_user)
        cuerpo = client.get(
            reverse("forum:perfil", kwargs={"username": verified_user.username})
        ).content.decode()
        assert perfil.rango_titulo in cuerpo
        assert perfil.color_rango in cuerpo

    def test_el_baneado_sale_como_game_over(self, client, verified_user):
        UserProfile.objects.create(user=verified_user, estado_usuario="baneado")
        cuerpo = client.get(
            reverse("forum:perfil", kwargs={"username": verified_user.username})
        ).content.decode()
        assert "Game Over" in cuerpo

    def test_el_perfil_lista_la_actividad(self, client, respuesta, verified_user):
        r = client.get(reverse("forum:perfil", kwargs={"username": verified_user.username}))
        assert list(r.context["ultimos_hilos"])
        assert list(r.context["ultimos_posts"])

    def test_el_badge_op_marca_al_autor_del_hilo(self, auth_client, hilo_abierto):
        cuerpo = auth_client.get(reverse("forum:hilo", kwargs={"pk": hilo_abierto.pk})).content.decode()
        assert ">OP<" in cuerpo


# ─── D4: botón global de nuevo hilo ───────────────────────

class TestBotonNuevoHilo:
    def test_el_verificado_ve_el_enlace(self, auth_client, db):
        cuerpo = auth_client.get(reverse("forum:index")).content.decode()
        assert reverse("forum:crear_hilo") in cuerpo

    def test_el_anonimo_no_lo_ve(self, client, db):
        cuerpo = client.get(reverse("forum:index")).content.decode()
        assert reverse("forum:crear_hilo") not in cuerpo

    def test_el_no_verificado_no_lo_ve(self, client, user, db):
        client.force_login(user, backend="django.contrib.auth.backends.ModelBackend")
        cuerpo = client.get(reverse("forum:index")).content.decode()
        assert reverse("forum:crear_hilo") not in cuerpo
