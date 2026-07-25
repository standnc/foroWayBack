from django.core.management.base import BaseCommand
from forum.models import Categoria

CATEGORIAS = [
    {
        "nombre": "🆕 Novedades ClashBang",
        "slug": "novedades-clashbang",
        "descripcion": "Actualidad, eventos y anuncios oficiales del foro moderno.",
        "orden": 1,
    },
    {
        "nombre": "💬 Charla General Nueva",
        "slug": "charla-general-nueva",
        "descripcion": "Temas variados, off-topic y comunidad activa 2026+.",
        "orden": 2,
    },
    {
        "nombre": "🌱 Cultivo Moderno",
        "slug": "cultivo-moderno",
        "descripcion": "Técnicas actuales, genética y fertilizantes modernos.",
        "orden": 3,
    },
    {
        "nombre": "⚔️ Arena y Combate",
        "slug": "arena-combate",
        "descripcion": "PvP, builds competitivos y estrategias actualizadas.",
        "orden": 4,
    },
    {
        "nombre": "🎨 Creatividad y Media",
        "slug": "creatividad-media",
        "descripcion": "Fanart, memes, música y contenido multimedia nuevo.",
        "orden": 5,
    },
    {
        "nombre": "❓ Soporte y Ayuda",
        "slug": "soporte-ayuda",
        "descripcion": "Dudas técnicas, bugs actuales y asistencia a usuarios nuevos.",
        "orden": 6,
    },
]


class Command(BaseCommand):
    help = "Crear las 6 categorías del Foro ClashBang (es_clashbang=True)"

    def handle(self, *args, **options):
        creadas = 0
        existentes = 0
        errores = 0

        for cat_data in CATEGORIAS:
            try:
                obj, created = Categoria.objects.get_or_create(
                    slug=cat_data["slug"],
                    defaults={
                        "nombre": cat_data["nombre"],
                        "descripcion": cat_data["descripcion"],
                        "orden": cat_data["orden"],
                        "es_clashbang": True,
                    },
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"✅ Creada: {obj.nombre}"))
                    creadas += 1
                else:
                    self.stdout.write(self.style.WARNING(f"⚠️  Ya existe: {obj.nombre}"))
                    existentes += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error con {cat_data['slug']}: {e}"))
                errores += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n📊 Resumen: {creadas} creadas, {existentes} existentes, {errores} errores"
        ))
