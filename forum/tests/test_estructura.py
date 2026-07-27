"""
Tests de la Fase 3: contadores, paginación y resolución de plantillas.
"""

import pytest
from django.template.loader import get_template
from django.urls import reverse

from forum.models import Categoria, Hilo
from forum.tests.conftest import CategoriaFactory, HiloFactory, PostFactory


class TestContadores:
    """Los contadores se muestran en categoria_list.html y nadie los mantenía."""

    def test_crear_un_hilo_sube_num_hilos(self, db, categoria):
        assert categoria.num_hilos == 0
        HiloFactory(categoria=categoria)
        categoria.refresh_from_db()
        assert categoria.num_hilos == 1

    def test_crear_un_post_sube_los_contadores(self, db, categoria):
        hilo = HiloFactory(categoria=categoria)
        PostFactory(hilo=hilo, orden=0)
        hilo.refresh_from_db()
        categoria.refresh_from_db()
        assert hilo.num_posts == 1
        assert categoria.num_posts == 1

    def test_borrar_un_post_baja_los_contadores(self, db, categoria):
        hilo = HiloFactory(categoria=categoria)
        post = PostFactory(hilo=hilo, orden=0)
        PostFactory(hilo=hilo, orden=1)
        post.delete()
        hilo.refresh_from_db()
        categoria.refresh_from_db()
        assert hilo.num_posts == 1
        assert categoria.num_posts == 1

    def test_borrar_un_hilo_baja_num_hilos(self, db, categoria):
        hilo = HiloFactory(categoria=categoria)
        HiloFactory(categoria=categoria)
        hilo.delete()
        categoria.refresh_from_db()
        assert categoria.num_hilos == 1

    def test_responder_por_la_vista_actualiza_los_contadores(self, auth_client, db):
        cat = CategoriaFactory(es_clashbang=True)
        hilo = HiloFactory(categoria=cat, es_historico=False)
        PostFactory(hilo=hilo, orden=0)
        auth_client.post(reverse("forum:hilo", kwargs={"pk": hilo.pk}), {"contenido": "respondo"})
        cat.refresh_from_db()
        hilo.refresh_from_db()
        assert hilo.num_posts == 2
        assert cat.num_posts == 2


class TestRecalcularContadores:
    def test_repara_contadores_desviados(self, db, categoria):
        from django.core.management import call_command

        hilo = HiloFactory(categoria=categoria)
        PostFactory(hilo=hilo, orden=0)
        # Se desvían a mano, saltándose las señales.
        Categoria.objects.filter(pk=categoria.pk).update(num_hilos=99, num_posts=99)
        Hilo.objects.filter(pk=hilo.pk).update(num_posts=99)

        call_command("recalcular_contadores")

        categoria.refresh_from_db()
        hilo.refresh_from_db()
        assert (categoria.num_hilos, categoria.num_posts) == (1, 1)
        assert hilo.num_posts == 1

    def test_dry_run_no_escribe(self, db, categoria):
        from django.core.management import call_command

        Categoria.objects.filter(pk=categoria.pk).update(num_hilos=42)
        call_command("recalcular_contadores", "--dry-run")
        categoria.refresh_from_db()
        assert categoria.num_hilos == 42


class TestPaginacion:
    def test_categoria_pagina_los_hilos(self, client, db):
        cat = CategoriaFactory()
        for _ in range(35):
            HiloFactory(categoria=cat)
        r = client.get(reverse("forum:categoria", kwargs={"slug": cat.slug}))
        assert r.status_code == 200
        assert len(r.context["hilos"]) == 30
        assert r.context["is_paginated"]
        assert r.context["categoria"] == cat

    def test_segunda_pagina_de_categoria(self, client, db):
        cat = CategoriaFactory()
        for _ in range(35):
            HiloFactory(categoria=cat)
        r = client.get(reverse("forum:categoria", kwargs={"slug": cat.slug}), {"page": 2})
        assert len(r.context["hilos"]) == 5

    def test_busqueda_pagina_los_resultados(self, client, db):
        cat = CategoriaFactory()
        for i in range(35):
            HiloFactory(categoria=cat, titulo=f"Resultado buscable {i}")
        r = client.get(reverse("forum:buscar"), {"q": "buscable"})
        assert len(r.context["resultados"]) == 30
        assert r.context["page_obj"].paginator.count == 35

    def test_busqueda_conserva_la_query_al_paginar(self, client, db):
        cat = CategoriaFactory()
        for i in range(35):
            HiloFactory(categoria=cat, titulo=f"Resultado buscable {i}")
        cuerpo = client.get(reverse("forum:buscar"), {"q": "buscable"}).content.decode()
        assert "q=buscable&amp;page=2" in cuerpo or "q=buscable&page=2" in cuerpo

    def test_busqueda_sin_query_sigue_dando_none(self, client, db):
        r = client.get(reverse("forum:buscar"))
        assert r.context["resultados"] is None

    def test_categoria_inexistente_da_404(self, client, db):
        assert client.get(reverse("forum:categoria", kwargs={"slug": "no-existe"})).status_code == 404


class TestPlantillas:
    """Tras borrar los huérfanos, cada nombre debe resolver a un único fichero."""

    @pytest.mark.parametrize(
        "nombre",
        [
            "forum/index.html",
            "forum/categoria_list.html",
            "forum/categoria_detail.html",
            "forum/hilo_detail.html",
            "forum/buscar.html",
            "forum/perfil.html",
            "forum/crear_hilo.html",
            "forum/verify_waiting.html",
            "forum/baneado.html",
            "forum/_paginacion.html",
            "forum/_login_form.html",
            "forum/_signup_form.html",
            "admin/log_viewer.html",
        ],
    )
    def test_la_plantilla_existe(self, nombre):
        assert get_template(nombre) is not None

    @pytest.mark.parametrize(
        "huerfana",
        ["index.html", "buscar.html", "perfil.html", "categoria_detail.html", "hilo_detail.html"],
    )
    def test_las_huerfanas_ya_no_existen(self, huerfana):
        from django.template import TemplateDoesNotExist

        with pytest.raises(TemplateDoesNotExist):
            get_template(huerfana)

    def test_la_portada_sirve_los_formularios_htmx(self, client, db):
        """La feature HTMX estaba en la plantilla muerta y no la veía nadie."""
        cuerpo = client.get(reverse("forum:index")).content.decode()
        assert 'id="login-form-container"' in cuerpo
        assert 'id="signup-form-container"' in cuerpo
        assert reverse("forum:inline_login") in cuerpo
        assert reverse("forum:inline_signup") in cuerpo

    def test_el_admin_usa_nuestro_index(self, staff_client):
        r = staff_client.get("/admin/")
        assert r.status_code == 200
        assert "admin/index.html" in [t.name for t in r.templates]


class TestPausaDeContadores:
    """migrar_sqlite pausa las señales y recalcula al final."""

    def test_las_senales_se_restauran_tras_la_pausa(self, db, categoria):
        from forum.signals import contadores_en_pausa

        with contadores_en_pausa():
            hilo = HiloFactory(categoria=categoria)
            PostFactory(hilo=hilo, orden=0)
            categoria.refresh_from_db()
            assert categoria.num_hilos == 0, "en pausa no se actualizan"

        PostFactory(hilo=hilo, orden=1)
        categoria.refresh_from_db()
        assert categoria.num_posts == 2, "al salir vuelven a funcionar"

    def test_la_pausa_se_deshace_aunque_falle(self, db, categoria):
        from forum.signals import contadores_en_pausa

        with pytest.raises(ValueError), contadores_en_pausa():
            raise ValueError("boom")

        HiloFactory(categoria=categoria)
        categoria.refresh_from_db()
        assert categoria.num_hilos == 1


class TestPlantillasSocialaccount:
    """Overrides de allauth que vivían solo en el VPS, fuera de git.

    authentication_error.html usaba {% url account_login %} sin comillas:
    Django lo trataba como variable de contexto y la página reventaba con
    NoReverseMatch justo cuando había que mostrar un error de login.
    """

    @pytest.mark.parametrize(
        "nombre", ["socialaccount/login.html", "socialaccount/authentication_error.html"]
    )
    def test_la_plantilla_renderiza(self, nombre, db, rf):
        from django.template.loader import render_to_string

        peticion = rf.get("/")
        html = render_to_string(nombre, {"provider": None, "process": "login"}, request=peticion)
        assert html.strip()

    def test_la_pagina_de_error_enlaza_al_login(self, db, rf):
        from django.template.loader import render_to_string
        from django.urls import reverse

        html = render_to_string(
            "socialaccount/authentication_error.html", {}, request=rf.get("/")
        )
        assert reverse("account_login") in html
        assert reverse("account_signup") in html


class TestArgumentosDeTagEntrecomillados:
    """Ningún tag de plantilla debe pasar literales sin comillas.

    Dos bugs del mismo tipo llegaron a producción: {% url account_login %} en
    authentication_error.html (NoReverseMatch, la página moría) y
    process=login en login/signup.html (traceback en el log en cada visita).
    Django los interpreta como variables de contexto, que no existen.

    Se comprueba de forma estática porque el fallo no siempre cambia el código
    de respuesta: un smoke test lo deja pasar.
    """

    RAICES = ["templates", "forum/templates"]

    def _plantillas(self):
        from pathlib import Path

        for raiz in self.RAICES:
            yield from Path(raiz).rglob("*.html")

    def test_url_siempre_lleva_el_nombre_entrecomillado(self):
        import re

        # {% url algo %} donde `algo` no empieza por comilla ni es una variable
        # con punto (p.ej. {% url hilo.get_absolute_url %} no aplica aquí).
        patron = re.compile(r"{%\s*url\s+(?![\"\'])([a-z_][a-z0-9_]*)\s*[%\s]")
        fallos = []
        for ruta in self._plantillas():
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                for m in patron.finditer(linea):
                    fallos.append(f"{ruta}:{n} -> {{% url {m.group(1)} %}}")
        assert not fallos, "nombres de URL sin comillas:\n" + "\n".join(fallos)

    def test_process_siempre_lleva_comillas(self):
        import re

        patron = re.compile(r"process=(?![\"\'])[a-z]")
        fallos = [
            f"{ruta}:{n}"
            for ruta in self._plantillas()
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1)
            if patron.search(linea)
        ]
        assert not fallos, "process= sin comillas en:\n" + "\n".join(fallos)

    def test_no_hay_comentarios_de_varias_lineas(self):
        """`{# ... #}` solo comenta una línea.

        En varias, Django no lo trata como comentario: imprime el texto en la
        página y parsea los tags que contenga. Ya ocurrió dos veces — la segunda
        llegó a producción con el comentario visible dentro del panel de login,
        porque este test cubría las comillas pero no los comentarios.
        """
        import re

        patron = re.compile(r"\{#(?:(?!#\}).)*?\n(?:(?!#\}).)*?#\}", re.S)
        fallos = []
        for ruta in self._plantillas():
            texto = ruta.read_text(encoding="utf-8")
            for m in patron.finditer(texto):
                linea = texto[: m.start()].count("\n") + 1
                fallos.append(f"{ruta}:{linea}")
        assert not fallos, (
            "comentarios {# #} de varias líneas (usa {% comment %}):\n" + "\n".join(fallos)
        )


class TestCssCompilado:
    """El CSS servido es un artefacto commiteado: puede quedar desfasado.

    static/css/app.css se genera con `npm run build:css` desde
    static/src/input.css. Se commitea porque el VPS no tiene Node: lo compila el
    CI. El riesgo es olvidarse de recompilar tras tocar el fuente o una
    plantilla, y desplegar estilos viejos. Estos tests lo detectan.
    """

    from pathlib import Path

    FUENTE = Path("static/src/input.css")
    COMPILADO = Path("static/css/app.css")

    def test_el_css_compilado_existe(self):
        assert self.COMPILADO.exists(), "falta static/css/app.css — ejecuta `npm run build:css`"

    def test_no_queda_tailwind_por_cdn(self):
        """El CDN compilaba en el navegador y obligaba a unsafe-eval en la CSP."""
        base = self.Path("templates/base.html").read_text(encoding="utf-8")
        assert "cdn.tailwindcss.com" not in base
        assert "css/app.css" in base

    def test_la_csp_ya_no_permite_el_cdn_de_tailwind(self):
        from django.conf import settings

        directivas = settings.CONTENT_SECURITY_POLICY["DIRECTIVES"]
        for clave in ("script-src", "style-src"):
            assert not any("tailwindcss.com" in o for o in directivas[clave]), clave

    def test_la_paleta_sunset_esta_en_el_compilado(self):
        """Guardarraíl de purgado: si Tailwind se lleva estas clases, el foro
        pierde su aspecto entero."""
        css = self.COMPILADO.read_text(encoding="utf-8")
        for clase in [
            ".card-sunset", ".btn-sunset", ".navbar-sunset", ".form-sunset",
            ".form-input-sunset", ".form-btn-primary", ".hero-title",
            ".stat-number", ".footer-sunset", "[x-cloak]",
        ]:
            assert clase in css, f"{clase} no está en el CSS compilado"

    def test_las_clases_de_los_formularios_sobreviven_al_purgado(self):
        """forum/forms.py define clases Tailwind en los widgets; si no está en
        `content` de tailwind.config.js, el purgado se las lleva."""
        css = self.COMPILADO.read_text(encoding="utf-8")
        # placeholder-slate-400 solo aparece en los widgets de forms.py, en
        # ninguna plantilla: si está en el CSS, `content` cubre el fichero.
        assert ".placeholder-slate-400" in css, (
            "clase de forum/forms.py purgada: falta './forum/forms.py' en "
            "`content` de tailwind.config.js"
        )
