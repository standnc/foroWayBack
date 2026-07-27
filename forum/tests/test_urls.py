"""
Tests de resolución de URLs: verificar que los nombres de ruta
devuelven las URLs esperadas.
"""

from django.urls import resolve, reverse


class TestURLs:
    def test_index_url(self):
        url = reverse("forum:index")
        assert url == "/"
        resolver = resolve(url)
        assert resolver.view_name == "forum:index"
        assert resolver.app_names == ["forum"]

    def test_categorias_url(self):
        url = reverse("forum:categorias")
        assert url == "/categorias/"
        resolver = resolve(url)
        assert resolver.view_name == "forum:categorias"

    def test_categoria_detail_url(self):
        url = reverse("forum:categoria", kwargs={"slug": "general"})
        assert url == "/categoria/general/"
        resolver = resolve(url)
        assert resolver.view_name == "forum:categoria"
        assert resolver.kwargs["slug"] == "general"

    def test_hilo_detail_url(self):
        url = reverse("forum:hilo", kwargs={"pk": 42})
        assert url == "/hilo/42/"
        resolver = resolve(url)
        assert resolver.view_name == "forum:hilo"
        assert resolver.kwargs["pk"] == 42

    def test_buscar_url(self):
        url = reverse("forum:buscar")
        assert url == "/buscar/"
        resolver = resolve(url)
        assert resolver.view_name == "forum:buscar"

    def test_admin_url(self):
        url = reverse("admin:index")
        assert url.startswith("/admin/")
