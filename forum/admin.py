from django.contrib import admin

from .models import Ban, Categoria, Hilo, Imagen, ModerationLog, Post, Report, Warning


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "num_hilos", "num_posts")
    prepopulated_fields = {"slug": ("nombre",)}
    search_fields = ("nombre",)


@admin.register(Hilo)
class HiloAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "autor_historico", "num_posts", "creado", "sticky", "cerrado")
    list_filter = ("categoria", "sticky", "cerrado", "es_historico")
    search_fields = ("titulo", "autor_historico")
    date_hierarchy = "creado"
    readonly_fields = ("num_posts", "num_vistas")


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hilo", "autor_historico", "orden", "creado", "es_historico")
    list_filter = ("es_historico",)
    search_fields = ("contenido", "autor_historico")
    date_hierarchy = "creado"
    readonly_fields = ("contenido_html",)


@admin.register(Imagen)
class ImagenAdmin(admin.ModelAdmin):
    list_display = ("__str__", "post", "descargada")
    list_filter = ("descargada",)
    search_fields = ("url_original",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("__str__", "tipo", "estado", "reportado_por", "creado")
    list_filter = ("tipo", "estado")
    search_fields = ("descripcion",)
    date_hierarchy = "creado"


@admin.register(Warning)
class WarningAdmin(admin.ModelAdmin):
    list_display = ("usuario", "moderador", "creado")
    list_filter = ("creado",)
    search_fields = ("usuario__email", "motivo")
    date_hierarchy = "creado"


@admin.register(Ban)
class BanAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "activo", "creado", "expira")
    list_filter = ("tipo", "activo")
    search_fields = ("usuario__email", "motivo")


@admin.register(ModerationLog)
class ModerationLogAdmin(admin.ModelAdmin):
    list_display = ("accion", "moderador", "creado")
    list_filter = ("accion",)
    date_hierarchy = "creado"
    readonly_fields = ("creado",)
