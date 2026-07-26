from django.core.management.base import BaseCommand
from forum.models import Categoria

CATEGORIAS = [
    {
        "orden": 1,
        "slug": "noticias",
        "nombre": "📰 Noticias",
        "descripcion": (
            "Anuncios oficiales, actualizaciones del servidor y comunicados "
            "del staff. Solo el equipo de moderación puede publicar en esta categoría."
        ),
    },
    {
        "orden": 2,
        "slug": "general",
        "nombre": "💬 General",
        "descripcion": (
            "Conversación diaria, presentaciones de nuevos usuarios y vida en "
            "la comunidad. Respeta a los demás usuarios y evita el spam."
        ),
    },
    {
        "orden": 3,
        "slug": "bleuga-beach",
        "nombre": "🏖️ Bleuga Beach",
        "descripcion": (
            "Zona relajada, humor, memes y off-topic ligero dentro del rol del "
            "servidor. Contenido apto para todos los públicos."
        ),
    },
    {
        "orden": 4,
        "slug": "soporte",
        "nombre": "🛠️ Soporte Técnico",
        "descripcion": (
            "Dudas sobre instalación, clientes, errores de conexión y "
            "configuración. Incluye logs y capturas cuando reportes un problema."
        ),
    },
    {
        "orden": 5,
        "slug": "minijuegos",
        "nombre": "🎮 Minijuegos",
        "descripcion": (
            "Concursos in-game, eventos de pesca, trivia y rankings de la "
            "comunidad. Publica aquí tus récords y participa en los retos semanales."
        ),
    },
    {
        "orden": 6,
        "slug": "off-topic",
        "nombre": "🌍 Off Topic",
        "descripcion": (
            "Temas completamente ajenos al servidor: otros juegos, tecnología, "
            "vida real. Mantén el respeto y evita temas polémicos."
        ),
    },
    {
        "orden": 7,
        "slug": "apelaciones",
        "nombre": "🛡️ Apelaciones y Moderación",
        "descripcion": (
            "Apelaciones de baneos, reportes de usuarios, bugs críticos y "
            "contacto directo con el equipo de staff. Usa el formato oficial "
            "para apelaciones."
        ),
    },
    {
        "orden": 8,
        "slug": "eventos",
        "nombre": "🎉 Eventos",
        "descripcion": (
            "Calendario de eventos especiales, torneos PvP y fiestas virtuales. "
            "Consulta las normas de participación antes de inscribirte."
        ),
    },
]


class Command(BaseCommand):
    help = "Crear/actualizar las 8 categorías del Foro ClashBang (es_clashbang=True)"

    def handle(self, *args, **options):
        creadas = 0
        actualizadas = 0
        errores = 0

        for cat_data in CATEGORIAS:
            slug = cat_data["slug"]
            try:
                obj, created = Categoria.objects.update_or_create(
                    slug=slug,
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
                    self.stdout.write(self.style.WARNING(f"🔄 Actualizada: {obj.nombre}"))
                    actualizadas += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error con '{slug}': {e}"))
                errores += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"📊 Resumen: {creadas} creadas, {actualizadas} actualizadas, {errores} errores"
        ))
