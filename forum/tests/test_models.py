"""
Tests de modelos del foro: creación, str, constraints, relaciones.
"""

import pytest
from datetime import datetime, timezone

from forum.models import Categoria, Hilo, Post, Imagen, Report, Warning, Ban, ModerationLog
from accounts.models import User


# ─── Categoria ──────────────────────────────────────────────

class TestCategoria:
    def test_crear_categoria(self, db):
        c = Categoria.objects.create(nombre="General", slug="general")
        assert c.pk is not None
        assert str(c) == "General"

    def test_get_absolute_url(self, categoria):
        url = categoria.get_absolute_url()
        assert url == f"/categoria/{categoria.slug}/"

    def test_ordering(self, db):
        Categoria.objects.create(nombre="Z", slug="z")
        Categoria.objects.create(nombre="A", slug="a")
        cats = list(Categoria.objects.all())
        assert cats[0].nombre == "A"
        assert cats[1].nombre == "Z"


# ─── Hilo ───────────────────────────────────────────────────

class TestHilo:
    def test_crear_hilo(self, hilo):
        assert hilo.pk is not None
        assert str(hilo).startswith("Título")
        assert hilo.autor is not None

    def test_hilo_historico(self, hilo_historico):
        assert hilo_historico.autor is None
        assert hilo_historico.autor_historico == "UsuarioWayBack"
        assert hilo_historico.es_historico is True

    def test_get_absolute_url(self, hilo):
        url = hilo.get_absolute_url()
        assert f"/hilo/{hilo.pk}/" in url

    def test_foreign_key_categoria(self, hilo, categoria):
        assert hilo.categoria == categoria
        assert categoria.hilos.count() >= 1

    def test_sticky_defaults_to_false(self, hilo):
        assert hilo.sticky is False

    def test_cerrado_defaults_to_false(self, hilo):
        assert hilo.cerrado is False


# ─── Post ───────────────────────────────────────────────────

class TestPost:
    def test_crear_post(self, post, hilo):
        assert post.pk is not None
        assert post.hilo == hilo
        assert str(post).startswith("Post")

    def test_foreign_key_hilo(self, post, hilo):
        assert hilo.posts.count() >= 1
        assert post.hilo == hilo

    def test_orden_secuencial(self, hilo, user):
        p1 = PostFactory(hilo=hilo, autor=user, orden=1)
        p2 = PostFactory(hilo=hilo, autor=user, orden=2)
        assert p1.orden < p2.orden

    def test_contenido_no_vacio(self, post):
        assert len(post.contenido) > 0


# ─── Imagen ─────────────────────────────────────────────────

class TestImagen:
    def test_crear_imagen(self, imagen, post):
        assert imagen.pk is not None
        assert imagen.post == post
        assert str(imagen).startswith("Imagen")

    def test_descargada_default(self, imagen):
        assert imagen.descargada is False

    def test_url_r2_vacio_por_defecto(self, imagen):
        assert imagen.url_r2 == ""


# ─── Report ─────────────────────────────────────────────────

class TestReport:
    def test_crear_report(self, report, post, user):
        assert report.pk is not None
        assert report.post == post
        assert report.reportado_por == user
        assert report.estado == "pendiente"

    def test_tipos_validos(self):
        tipos = dict(Report.TIPOS)
        assert "spam" in tipos
        assert "acoso" in tipos
        assert "discurso_odio" in tipos

    def test_estados_validos(self):
        estados = dict(Report.ESTADOS)
        assert "pendiente" in estados
        assert "resuelto" in estados


# ─── Warning ────────────────────────────────────────────────

class TestWarning:
    def test_crear_advertencia(self, advertencia, user, moderator):
        assert advertencia.pk is not None
        assert advertencia.usuario == user
        assert advertencia.moderador == moderator
        assert str(advertencia).startswith("Advertencia")

    def test_creado_automatico(self, advertencia):
        assert advertencia.creado is not None


# ─── Ban ────────────────────────────────────────────────────

class TestBan:
    def test_crear_ban(self, ban, user, moderator):
        assert ban.pk is not None
        assert ban.usuario == user
        assert ban.moderador == moderator
        assert ban.activo is True

    def test_ban_temporal(self, ban):
        assert ban.tipo == "temporal"
        assert ban.expira is not None

    def test_ban_permanente(self, db, user, moderator):
        permaban = Ban.objects.create(
            usuario=user, moderador=moderator,
            motivo="Vandalismo grave", tipo="permanente"
        )
        assert permaban.tipo == "permanente"
        assert permaban.expira is None


# ─── ModerationLog ──────────────────────────────────────────

class TestModerationLog:
    def test_crear_log(self, db, moderator, post):
        log = ModerationLog.objects.create(
            moderador=moderator,
            accion="editar_post",
            descripcion="Editado contenido ofensivo",
            target_post=post,
        )
        assert log.pk is not None
        assert log.get_accion_display() == "Editar post"

    def test_acciones_validas(self):
        acciones = dict(ModerationLog.ACCIONES)
        assert "borrar_post" in acciones
        assert "banear" in acciones
        assert "levantar_ban" in acciones


# ─── User (accounts) ────────────────────────────────────────

class TestUser:
    def test_crear_usuario(self, user):
        assert user.pk is not None
        assert "@" in user.email

    def test_crear_superuser(self, db):
        admin = User.objects.create_superuser(
            email="admin@test.com", password="admin123"
        )
        assert admin.is_staff
        assert admin.is_superuser

    def test_email_unique(self, db):
        User.objects.create_user(email="dup@test.com", password="pass1")
        with pytest.raises(Exception):
            User.objects.create_user(email="dup@test.com", password="pass2")


# ─── Relaciones complejas ──────────────────────────────────

class TestRelationships:
    def test_hilo_tiene_posts(self, hilo_con_posts):
        assert hilo_con_posts.posts.count() == 5

    def test_post_pertenece_a_hilo(self, post, hilo):
        assert post.hilo == hilo

    def test_categoria_tiene_hilos(self, categoria, hilo):
        assert categoria.hilos.count() >= 1

    def test_usuario_tiene_hilos(self, user, hilo):
        assert user.hilos.count() >= 1

    def test_usuario_tiene_posts(self, user, post):
        assert user.posts.count() >= 1

    def test_post_tiene_imagenes(self, post, imagen):
        assert post.imagenes.count() >= 1


# Import PostFactory for test_orden_secuencial
from .conftest import PostFactory
