from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Categoria(models.Model):
    """
    Categorías planas del foro (26 categorías del scrape).
    Sin anidamiento — los datos originales no tienen jerarquía.
    """
    id_original = models.IntegerField(unique=True, null=True, blank=True)
    slug = models.SlugField(unique=True, max_length=100)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    es_clashbang = models.BooleanField(default=False, help_text="True = Foro ClashBang (nuevo), False = Archivo Histórico")
    orden = models.PositiveIntegerField(default=0, help_text="Orden de visualización (menor = primero)")
    # Contadores (actualizados por señales o save() de Hilo/Post)
    num_hilos = models.PositiveIntegerField(default=0, editable=False)
    num_posts = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["id_original"]),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("forum:categoria", kwargs={"slug": self.slug})

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    rango_titulo = models.CharField(max_length=50, default='Hijo de Fr4n')
    puntos_barra = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    estado_usuario = models.CharField(
        max_length=20,
        default='activo',
        choices=[('activo','Activo'), ('baneado','Game Over'), ('desaparecido','Desaparecido')]
    )
    color_rango = models.CharField(max_length=7, default='#94a3b8')

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f"Perfil de {self.user.email}"

    @property
    def mensajes_count(self):
        return self.user.posts.count()

    @property
    def is_game_over(self):
        return self.estado_usuario in ('baneado', 'desaparecido')


class Hilo(models.Model):
    """
    Hilo/tema histórico (scrape) o nuevo.
    - autor es nullable: los hilos históricos no tienen cuenta real
    - autor_historico guarda el nombre del scrape
    """
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="hilos"
    )
    id_original = models.IntegerField(unique=True, null=True, blank=True)
    titulo = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hilos",
    )
    autor_historico = models.CharField(max_length=100, blank=True)
    url_original = models.URLField(blank=True)
    archivo_html = models.CharField(max_length=255, blank=True)
    es_historico = models.BooleanField(default=True)
    sticky = models.BooleanField(default=False)
    cerrado = models.BooleanField(default=False)
    contenido_apertura = models.TextField(blank=True)

    # Contadores
    num_posts = models.PositiveIntegerField(default=0, editable=False)
    num_vistas = models.PositiveIntegerField(default=0)

    # default en vez de auto_now_add: migrar_sqlite escribe fechas de 2009 del
    # scrape y auto_now_add las machacaría con la fecha de importación.
    creado = models.DateTimeField(default=timezone.now)
    ultimo_post = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-sticky", "-ultimo_post"]
        verbose_name = "hilo"
        verbose_name_plural = "hilos"
        indexes = [
            models.Index(fields=["categoria", "-ultimo_post"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["id_original"]),
        ]

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return reverse("forum:hilo", kwargs={"pk": self.pk})


class Post(models.Model):
    """
    Post individual (histórico o nuevo).
    - autor es nullable: posts históricos sin cuenta real
    - orden: posición dentro del hilo (1 = primer post, 2 = respuesta, etc.)
    - msg_id: ID del mensaje SMF original (vacío en el scrape pero reservado)
    """
    hilo = models.ForeignKey(
        Hilo, on_delete=models.CASCADE, related_name="posts"
    )
    id_original = models.IntegerField(unique=True, null=True, blank=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    autor_historico = models.CharField(max_length=100, blank=True)
    msg_id = models.CharField(max_length=50, blank=True)
    orden = models.PositiveIntegerField(default=0)
    contenido = models.TextField()
    contenido_html = models.TextField(blank=True)
    # Ver nota en Hilo.creado: default, no auto_now_add.
    creado = models.DateTimeField(default=timezone.now)
    editado = models.DateTimeField(null=True, blank=True)
    es_historico = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden"]
        verbose_name = "post"
        verbose_name_plural = "posts"
        indexes = [
            models.Index(fields=["hilo", "orden"]),
            models.Index(fields=["autor"]),
            models.Index(fields=["id_original"]),
        ]

    def __str__(self):
        return f"Post #{self.pk} en {self.hilo}"


class Imagen(models.Model):
    """
    Imagen asociada a un post (del scrape o subida nueva).
    url_original: URL de web.archive.org del scrape
    url_r2: URL en Cloudflare R2 tras migración
    """
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="imagenes"
    )
    url_original = models.URLField()
    url_r2 = models.URLField(blank=True)
    archivo_local = models.CharField(max_length=255, blank=True)
    descargada = models.BooleanField(default=False)

    class Meta:
        verbose_name = "imagen"
        verbose_name_plural = "imágenes"
        indexes = [
            models.Index(fields=["post"]),
            models.Index(fields=["descargada"]),
        ]

    def __str__(self):
        return f"Imagen #{self.pk} → Post #{self.post_id}"


class Report(models.Model):
    """
    Reporte de un post/hilo por contenido inapropiado.
    """
    TIPOS = [
        ("spam", "Spam"),
        ("acoso", "Acoso"),
        ("contenido_inapropiado", "Contenido inapropiado"),
        ("discurso_odio", "Discurso de odio"),
        ("otro", "Otro"),
    ]

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("revisando", "En revisión"),
        ("resuelto", "Resuelto"),
        ("rechazado", "Rechazado"),
    ]

    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, null=True, blank=True, related_name="reportes"
    )
    hilo = models.ForeignKey(
        Hilo, on_delete=models.CASCADE, null=True, blank=True, related_name="reportes"
    )
    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reportes_hechos",
    )
    tipo = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    creado = models.DateTimeField(auto_now_add=True)
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reportes_resueltos",
    )
    resuelto_en = models.DateTimeField(null=True, blank=True)
    nota_moderacion = models.TextField(blank=True)

    class Meta:
        verbose_name = "reporte"
        verbose_name_plural = "reportes"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["creado"]),
        ]

    def __str__(self):
        return f"Reporte #{self.pk} - {self.get_tipo_display()} ({self.get_estado_display()})"


class Warning(models.Model):
    """
    Advertencia a un usuario por mala conducta.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="advertencias",
    )
    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="advertencias_emitidas",
    )
    motivo = models.TextField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "advertencia"
        verbose_name_plural = "advertencias"
        ordering = ["-creado"]

    def __str__(self):
        return f"Advertencia a {self.usuario} (por {self.moderador})"


class Ban(models.Model):
    """
    Suspensión/baneo de un usuario.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="baneos",
    )
    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="baneos_emitidos",
    )
    motivo = models.TextField()
    tipo = models.CharField(
        max_length=10,
        choices=[("temporal", "Temporal"), ("permanente", "Permanente")],
        default="temporal",
    )
    activo = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField(null=True, blank=True)
    levantado = models.DateTimeField(null=True, blank=True)
    levantado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="baneos_levantados",
    )

    class Meta:
        verbose_name = "baneo"
        verbose_name_plural = "baneos"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["usuario", "activo"]),
        ]

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"Ban a {self.usuario} - {estado}"


class ModerationLog(models.Model):
    """
    Registro de acciones de moderación (auditoría).
    """
    ACCIONES = [
        ("editar_post", "Editar post"),
        ("borrar_post", "Borrar post"),
        ("cerrar_hilo", "Cerrar hilo"),
        ("abrir_hilo", "Abrir hilo"),
        ("mover_hilo", "Mover hilo"),
        ("editar_usuario", "Editar usuario"),
        ("banear", "Bannear usuario"),
        ("levantar_ban", "Levantar baneo"),
        ("advertir", "Advertir usuario"),
        ("resolver_reporte", "Resolver reporte"),
    ]

    moderador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="acciones_moderacion",
    )
    accion = models.CharField(max_length=30, choices=ACCIONES)
    descripcion = models.TextField()
    target_post = models.ForeignKey(
        Post, on_delete=models.SET_NULL, null=True, blank=True
    )
    target_hilo = models.ForeignKey(
        Hilo, on_delete=models.SET_NULL, null=True, blank=True
    )
    target_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderado_en",
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "log de moderación"
        verbose_name_plural = "logs de moderación"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["creado"]),
            models.Index(fields=["moderador"]),
        ]

    def __str__(self):
        return f"{self.get_accion_display()} por {self.moderador} ({self.creado})"
