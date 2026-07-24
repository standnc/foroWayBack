"""
Tests de vistas del foro: status codes, templates usados, contexto, búsqueda.
"""

import pytest
from django.urls import reverse
from forum.models import Categoria, Hilo, Post


# ─── Smoke tests: todas las páginas responden 200 ──────────

class TestSmoke:
    """Tests mínimos (smoke) para verificar que nada está roto."""

    @pytest.mark.django_db
    def test_index_200(self, client):
        r = client.get(reverse("forum:index"))
        assert r.status_code == 200

    def test_categorias_200(self, client, categorias_varias):
        r = client.get(reverse("forum:categorias"))
        assert r.status_code == 200

    def test_categoria_detail_200(self, client, categoria):
        r = client.get(reverse("forum:categoria", kwargs={"slug": categoria.slug}))
        assert r.status_code == 200

    def test_hilo_detail_200(self, client, hilo):
        r = client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk}))
        assert r.status_code == 200

    @pytest.mark.django_db
    def test_buscar_200(self, client):
        r = client.get(reverse("forum:buscar"))
        assert r.status_code == 200

    def test_buscar_con_query_200(self, client, hilo):
        r = client.get(reverse("forum:buscar"), {"q": hilo.titulo[:10]})
        assert r.status_code == 200

    @pytest.mark.django_db
    def test_buscar_sin_resultados(self, client):
        r = client.get(reverse("forum:buscar"), {"q": "xzxyzwz"})
        assert r.status_code == 200

    @pytest.mark.django_db
    def test_hilo_404(self, client):
        r = client.get(reverse("forum:hilo", kwargs={"pk": 99999}))
        assert r.status_code == 404

    @pytest.mark.django_db
    def test_categoria_404(self, client):
        r = client.get(reverse("forum:categoria", kwargs={"slug": "no-existe"}))
        assert r.status_code == 404


# ─── Templates correctos ──────────────────────────────────

class TestTemplates:
    @pytest.mark.django_db
    def test_index_template(self, client):
        r = client.get(reverse("forum:index"))
        assert "forum/index.html" in [t.name for t in r.templates]

    def test_categorias_template(self, client, categorias_varias):
        r = client.get(reverse("forum:categorias"))
        assert "forum/categoria_list.html" in [t.name for t in r.templates]

    def test_categoria_detail_template(self, client, categoria):
        r = client.get(reverse("forum:categoria", kwargs={"slug": categoria.slug}))
        assert "forum/categoria_detail.html" in [t.name for t in r.templates]

    def test_hilo_detail_template(self, client, hilo):
        r = client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk}))
        assert "forum/hilo_detail.html" in [t.name for t in r.templates]

    def test_buscar_template(self, client):
        r = client.get(reverse("forum:buscar"))
        assert "forum/buscar.html" in [t.name for t in r.templates]

    @pytest.mark.django_db
    def test_base_template_usado(self, client, categoria):
        """Todas las páginas heredan de base.html."""
        r = client.get(reverse("forum:index"))
        template_names = [t.name for t in r.templates]
        assert "base.html" in template_names


# ─── Contexto de las vistas ──────────────────────────────

class TestContext:
    def test_index_stats(self, client, hilo, post, user):
        """Index tiene stats con valores correctos."""
        r = client.get(reverse("forum:index"))
        stats = r.context.get("stats", [])
        stats_dict = {s["etiqueta"]: s["valor"] for s in stats}
        assert stats_dict["Categorías"] >= 1
        assert stats_dict["Hilos"] >= 1
        assert stats_dict["Posts"] >= 1
        assert stats_dict["Usuarios"] >= 1

    def test_index_categorias(self, client, categoria):
        """Index lista categorías."""
        r = client.get(reverse("forum:index"))
        cats = list(r.context.get("categorias", []))
        assert len(cats) >= 1

    def test_categoria_list_context(self, client, categorias_varias):
        """Lista de categorías tiene todas."""
        r = client.get(reverse("forum:categorias"))
        cats = list(r.context.get("categorias", []))
        assert len(cats) == 3

    def test_categoria_detail_hilos(self, client, categoria, hilo):
        """Vista de categoría tiene sus hilos."""
        r = client.get(reverse("forum:categoria", kwargs={"slug": categoria.slug}))
        hilos = list(r.context.get("hilos", []))
        assert len(hilos) >= 1
        assert r.context["categoria"] == categoria

    def test_hilo_detail_posts(self, client, hilo, post):
        """Vista de hilo tiene sus posts."""
        r = client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk}))
        posts = list(r.context.get("posts", []))
        assert len(posts) >= 1
        assert r.context["hilo"] == hilo

    def test_buscar_resultados(self, client, hilo):
        """Búsqueda encuentra hilos por título."""
        r = client.get(reverse("forum:buscar"), {"q": hilo.titulo[:5]})
        resultados = r.context.get("resultados")
        assert resultados is not None
        assert len(resultados) >= 1
        assert hilo in resultados

    def test_buscar_sin_query_no_resultados(self, client):
        """Sin query, resultados es None."""
        r = client.get(reverse("forum:buscar"))
        assert r.context.get("resultados") is None


# ─── Posts ordenados correctamente ────────────────────────

class TestOrdenPosts:
    def test_posts_orden_correcto(self, client, hilo_con_posts):
        """Posts se muestran en orden ascendente (1, 2, 3, 4, 5)."""
        r = client.get(reverse("forum:hilo", kwargs={"pk": hilo_con_posts.pk}))
        posts = list(r.context.get("posts", []))
        ordenes = [p.orden for p in posts]
        assert ordenes == sorted(ordenes), "Los posts deben estar ordenados por 'orden'"

    def test_posts_no_invertidos(self, client, hilo, user):
        """Más posts: confirmar que no están al revés."""
        from forum.tests.conftest import PostFactory
        for i in range(3):
            PostFactory(hilo=hilo, autor=user, orden=i + 1)
        r = client.get(reverse("forum:hilo", kwargs={"pk": hilo.pk}))
        posts = list(r.context.get("posts", []))
        ordenes = [p.orden for p in posts]
        assert ordenes == sorted(ordenes)
