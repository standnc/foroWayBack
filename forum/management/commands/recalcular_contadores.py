from django.core.management.base import BaseCommand
from django.db.models import Count

from forum.models import Categoria, Hilo


class Command(BaseCommand):
    help = "Recalcula los contadores denormalizados de categorías e hilos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que cambiaría sin escribir en la base de datos.",
        )

    def handle(self, *args, **options):
        seco = options["dry_run"]
        if seco:
            self.stdout.write(self.style.WARNING("Modo dry-run: no se escribe nada."))

        # Hilo.num_posts: el comando anterior no lo tocaba y quedaba desfasado
        # respecto a lo que migrar_sqlite había importado.
        hilos_cambiados = 0
        for hilo in Hilo.objects.annotate(real=Count("posts")):
            if hilo.num_posts == hilo.real:
                continue
            hilos_cambiados += 1
            if not seco:
                Hilo.objects.filter(pk=hilo.pk).update(num_posts=hilo.real)

        cats_cambiadas = 0
        total_cats = 0
        for cat in Categoria.objects.annotate(
            hilos_count=Count("hilos", distinct=True),
            posts_count=Count("hilos__posts", distinct=True),
        ):
            total_cats += 1
            if cat.num_hilos == cat.hilos_count and cat.num_posts == cat.posts_count:
                continue
            cats_cambiadas += 1
            self.stdout.write(
                f"  {cat.nombre}: hilos {cat.num_hilos}→{cat.hilos_count}, "
                f"posts {cat.num_posts}→{cat.posts_count}"
            )
            if not seco:
                Categoria.objects.filter(pk=cat.pk).update(
                    num_hilos=cat.hilos_count, num_posts=cat.posts_count
                )

        verbo = "cambiarían" if seco else "actualizadas"
        self.stdout.write(self.style.SUCCESS(
            f"✅ {cats_cambiadas}/{total_cats} categorías {verbo} · "
            f"{hilos_cambiados} hilos {verbo}"
        ))
