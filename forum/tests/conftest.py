"""
Fixtures compartidas para todos los tests del foro.

Usa factory_boy para generar datos de prueba limpios y repetibles.
"""

from datetime import UTC, datetime

import pytest
from factory import Faker, Sequence, SubFactory
from factory.django import DjangoModelFactory

from accounts.models import User
from forum.models import Ban, Categoria, Hilo, Imagen, Post, Report, Warning

# ─── Factories ───────────────────────────────────────────────

class UserFactory(DjangoModelFactory):
    """Crea usuarios de prueba con email único."""
    class Meta:
        model = User

    email = Sequence(lambda n: f"user{n}@test.clashbang.forum")
    username = Sequence(lambda n: f"user{n}")
    bio = Faker("sentence")
    firma = Faker("sentence")


class CategoriaFactory(DjangoModelFactory):
    """Crea categorías de prueba."""
    class Meta:
        model = Categoria

    nombre = Sequence(lambda n: f"Categoría {n}")
    slug = Sequence(lambda n: f"categoria-{n}")
    descripcion = Faker("sentence")


class HiloFactory(DjangoModelFactory):
    """Crea hilos de prueba."""
    class Meta:
        model = Hilo

    categoria = SubFactory(CategoriaFactory)
    titulo = Sequence(lambda n: f"Título del hilo {n}")
    slug = Sequence(lambda n: f"titulo-del-hilo-{n}")
    autor = SubFactory(UserFactory)
    creado = Faker("date_time_this_decade", tzinfo=UTC)
    ultimo_post = Faker("date_time_this_decade", tzinfo=UTC)


class PostFactory(DjangoModelFactory):
    """Crea posts de prueba."""
    class Meta:
        model = Post

    hilo = SubFactory(HiloFactory)
    autor = SubFactory(UserFactory)
    contenido = Faker("paragraph")
    creado = Faker("date_time_this_decade", tzinfo=UTC)
    orden = Sequence(lambda n: n % 10 + 1)


class ImagenFactory(DjangoModelFactory):
    """Crea imágenes de prueba."""
    class Meta:
        model = Imagen

    post = SubFactory(PostFactory)
    url_original = Faker("url")


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture
def user(db):
    """Usuario básico."""
    return UserFactory()


@pytest.fixture
def verified_user(db):
    """Usuario con el email confirmado: el único que atraviesa VerifiedRequiredMixin."""
    return UserFactory(is_verified=True)


@pytest.fixture
def moderator(db):
    """Usuario moderador (staff)."""
    return UserFactory(is_staff=True, is_verified=True)


@pytest.fixture
def auth_client(client, verified_user):
    """Cliente autenticado con un usuario verificado.

    El backend se pasa explícito porque AUTHENTICATION_BACKENDS empieza por
    AxesStandaloneBackend y force_login usaría ese por defecto.
    """
    client.force_login(verified_user, backend="django.contrib.auth.backends.ModelBackend")
    return client


@pytest.fixture
def staff_client(client, moderator):
    """Cliente autenticado con un moderador (staff)."""
    client.force_login(moderator, backend="django.contrib.auth.backends.ModelBackend")
    return client


@pytest.fixture
def categoria(db):
    """Una categoría."""
    return CategoriaFactory()


@pytest.fixture
def hilo(db, categoria, user):
    """Hilo con categoría y autor."""
    return HiloFactory(categoria=categoria, autor=user)


@pytest.fixture
def hilo_historico(db, categoria):
    """Hilo histórico (sin autor real)."""
    return HiloFactory(
        categoria=categoria,
        autor=None,
        autor_historico="UsuarioWayBack",
        es_historico=True,
    )


@pytest.fixture
def post(db, hilo, user):
    """Post dentro de un hilo."""
    return PostFactory(hilo=hilo, autor=user, orden=1)


@pytest.fixture
def imagen(db, post):
    """Imagen asociada a un post."""
    return ImagenFactory(post=post)


@pytest.fixture
def ban(db, user, moderator):
    """Baneo de usuario."""
    return Ban.objects.create(
        usuario=user,
        moderador=moderator,
        motivo="Spam en el foro",
        tipo="temporal",
        expira=datetime(2027, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def report(db, post, user):
    """Reporte de un post."""
    return Report.objects.create(
        post=post,
        reportado_por=user,
        tipo="spam",
        descripcion="Post con publicidad",
    )


@pytest.fixture
def advertencia(db, user, moderator):
    """Advertencia a un usuario."""
    return Warning.objects.create(
        usuario=user,
        moderador=moderator,
        motivo="Comportamiento inapropiado",
    )


@pytest.fixture
def categorias_varias(db):
    """Tres categorías de prueba."""
    return [
        CategoriaFactory(nombre="General", slug="general"),
        CategoriaFactory(nombre="Soporte", slug="soporte"),
        CategoriaFactory(nombre="Off-topic", slug="off-topic"),
    ]


@pytest.fixture
def hilo_con_posts(db, categoria, user):
    """Hilo con 5 posts de distintos autores."""
    h = HiloFactory(categoria=categoria, autor=user, titulo="Hilo con respuestas")
    for i in range(5):
        PostFactory(hilo=h, autor=user, orden=i + 1, contenido=f"Post número {i + 1}")
    return h
