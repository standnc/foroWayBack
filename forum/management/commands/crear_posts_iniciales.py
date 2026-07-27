from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from forum.models import Categoria, Hilo, Post

User = get_user_model()

STICKY_POSTS = [
    {
        "slug": "noticias",
        "titulo": "📰 Bienvenido a Noticias — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "Aquí se publican **anuncios oficiales**, actualizaciones del servidor "
            "y comunicados del equipo de moderación. Es el punto de referencia "
            "para estar al día de todo lo que ocurre en ClashBang.\n\n"
            "**Normas básicas:**\n"
            "• Solo el **staff** puede abrir hilos aquí.\n"
            "• Los comentarios están abiertos para que preguntes dudas sobre cada anuncio.\n"
            "• No se permite debate político ni religioso en los comentarios.\n"
            "• Hilo cerrado = discusión terminada. No reabrir.\n\n"
            "Gracias por leernos. ¡Que disfrutes del foro! 🎮"
        ),
    },
    {
        "slug": "general",
        "titulo": "💬 Bienvenido a General — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "La **plaza mayor** de ClashBang. Aquí se conversa de todo: "
            "presentaciones de nuevos usuarios, vida en la comunidad, "
            "anécdotas del juego, preguntas rápidas… el día a día del foro.\n\n"
            "**Normas básicas:**\n"
            "• **Respeta** a los demás usuarios. Cero insultos o acoso.\n"
            "• Evita el **spam**: no publiques el mismo mensaje varias veces.\n"
            "• No compartas **datos personales** (ni tuyos ni de otros).\n"
            "• Mantén un tono constructivo. Todos fuimos nuevos alguna vez.\n\n"
            "¡Preséntate y cuéntanos quién eres! 👋"
        ),
    },
    {
        "slug": "bleuga-beach",
        "titulo": "🏖️ Bienvenido a Bleuga Beach — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "La **zona relax** del foro. Humor, memes, historias graciosas y "
            "off-topic ligero dentro del rol del servidor. Piensa en ello como "
            "la playa virtual de ClashBang: a tomar algo y desconectar.\n\n"
            "**Normas básicas:**\n"
            "• Contenido **apto para todos los públicos** (nada +18).\n"
            "• Los memes y el humor son bienvenidos, pero sin pasarse.\n"
            "• Nada de **política, religión** o temas sensibles.\n"
            "• Si el moderador te dice que te pasaste, es que te pasaste.\n\n"
            "¡Coge tu toalla y disfruta! 🌴"
        ),
    },
    {
        "slug": "soporte",
        "titulo": "🛠️ Bienvenido a Soporte Técnico — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "¿Tienes un problema con el juego? ¿No puedes conectar, "
            "el cliente falla, algo no funciona como debería? "
            "Este es tu sitio.\n\n"
            "**Normas básicas:**\n"
            "• **Busca antes de preguntar**: puede que tu duda ya esté resuelta.\n"
            "• Sé **específico**: versión del cliente, sistema operativo, "
            "pasos para reproducir el error.\n"
            "• Incluye **logs o capturas** cuando sea posible.\n"
            "• No etiquetes al staff innecesariamente — revisamos todos los hilos.\n\n"
            "Entre todos nos ayudamos. ¡Gracias por tu paciencia! 🔧"
        ),
    },
    {
        "slug": "minijuegos",
        "titulo": "🎮 Bienvenido a Minijuegos — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "Concursos in-game, eventos de pesca, trivia, rankings "
            "y todo lo que sea competir sanamente en ClashBang. "
            "Publica aquí tus récords y participa en los retos semanales.\n\n"
            "**Normas básicas:**\n"
            "• **No hagas trampas** — los ganadores se verifican.\n"
            "• Sigue las instrucciones de cada concurso al pie de la letra.\n"
            "• Un mismo usuario no puede ganar premios con múltiples cuentas.\n"
            "• Respeta a los organizadores y a los demás participantes.\n\n"
            "¡Que gane el mejor! 🏆"
        ),
    },
    {
        "slug": "off-topic",
        "titulo": "🌍 Bienvenido a Off Topic — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "Temas **completamente ajenos** a ClashBang: otros juegos, "
            "música, series, tecnología, debates ligeros, vida real… "
            "Si no encaja en ninguna otra categoría, probablemente va aquí.\n\n"
            "**Normas básicas:**\n"
            "• **Respeto por encima de todo.** Puedes discrepar sin faltar.\n"
            "• Evita temas **polémicos** (política, religión, drogas…).\n"
            "• No compartas **enlaces sospechosos** ni contenido pirateado.\n"
            "• El sentido común es la mejor norma.\n\n"
            "A todo se le puede dar un enfoque interesante. ¡A conversar! 🗣️"
        ),
    },
    {
        "slug": "apelaciones",
        "titulo": "🛡️ Bienvenido a Apelaciones y Moderación — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "Si has recibido un **baneo o advertencia** y crees que "
            "hubo un error, este es el lugar para apelar. También se "
            "reportan aquí bugs críticos y se contacta al staff.\n\n"
            "**Normas básicas:**\n"
            "• **Usa el formato oficial** de apelación (estará fijado).\n"
            "• Sé **honesto**: mentir en una apelación la invalida.\n"
            "• No abras **múltiples hilos** para la misma apelación.\n"
            "• El equipo de moderación responde en un plazo de **48-72h**.\n"
            "• Las decisiones finales son del staff. Recurrir con respeto.\n\n"
            "Todos merecemos una segunda oportunidad. ⚖️"
        ),
    },
    {
        "slug": "eventos",
        "titulo": "🎉 Bienvenido a Eventos — Normas y propósito",
        "contenido": (
            "**¿De qué va este foro?**\n\n"
            "Calendario de **eventos especiales**: torneos PvP, "
            "fiestas virtuales, celebraciones de temporada, "
            "cacerías y todo lo que organice la comunidad.\n\n"
            "**Normas básicas:**\n"
            "• **Lee las normas** de cada evento antes de inscribirte.\n"
            "• Respeta los horarios — la puntualidad cuenta.\n"
            "• Un solo registro por persona (salvo que se indique lo contrario).\n"
            "• Los organizadores tienen la última palabra.\n\n"
            "¡La diversión está asegurada! 🎪"
        ),
    },
]


class Command(BaseCommand):
    help = "Crea un hilo sticky del Admin en cada categoría ClashBang vacía"

    def handle(self, *args, **options):
        try:
            admin = User.objects.get(is_superuser=True)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ No hay superusuario admin"))
            return

        creados = 0
        existentes = 0
        errores = 0

        for data in STICKY_POSTS:
            slug = data["slug"]
            try:
                cat = Categoria.objects.get(slug=slug, es_clashbang=True)
            except Categoria.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"⚠️ No existe categoría con slug='{slug}'")
                )
                errores += 1
                continue

            # Si la categoría ya tiene algún hilo NO histórico, saltar
            hilos_no_historicos = Hilo.objects.filter(
                categoria=cat, es_historico=False
            ).count()
            if hilos_no_historicos > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⏭️ {cat.nombre} ya tiene {hilos_no_historicos} hilo(s) nuevo(s)"
                    )
                )
                existentes += 1
                continue

            titulo = data["titulo"]
            hilo_slug = slugify(titulo)[:50]

            ahora = timezone.now()
            hilo = Hilo.objects.create(
                categoria=cat,
                titulo=titulo,
                slug=hilo_slug,
                autor=admin,
                sticky=True,
                cerrado=False,
                es_historico=False,
                contenido_apertura=data["contenido"],
                creado=ahora,
                ultimo_post=ahora,
            )
            Post.objects.create(
                hilo=hilo,
                autor=admin,
                contenido=data["contenido"],
                creado=ahora,
            )

            cat.num_hilos = Hilo.objects.filter(categoria=cat).count()
            cat.num_posts = Post.objects.filter(hilo__categoria=cat).count()
            cat.save(update_fields=["num_hilos", "num_posts"])

            self.stdout.write(self.style.SUCCESS(f"✅ Sticky creado en {cat.nombre}"))
            creados += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"📊 Resumen: {creados} creados, {existentes} existentes, {errores} errores"
            )
        )
