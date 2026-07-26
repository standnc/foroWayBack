from django.db.models import Count
from django.core.management.base import BaseCommand
from forum.models import Categoria


class Command(BaseCommand):
    help = "Recalcula num_hilos y num_posts de todas las categorías"

    def handle(self, *args, **options):
        total = Categoria.objects.count()
        ok = 0

        for cat in Categoria.objects.annotate(
            hilos_count=Count("hilos", distinct=True),
            posts_count=Count("hilos__posts", distinct=True),
        ):
            cat.num_hilos = cat.hilos_count
            cat.num_posts = cat.posts_count
            cat.save(update_fields=["num_hilos", "num_posts"])
            ok += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ {ok}/{total} categorías actualizadas"
        ))
