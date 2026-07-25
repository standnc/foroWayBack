from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from forum.signals import actualizar_perfil

User = get_user_model()

class Command(BaseCommand):
    help = 'Poblar perfiles de usuario existentes basado en sus posts'

    def handle(self, *args, **options):
        users = User.objects.filter(is_active=True)
        total = users.count()
        self.stdout.write(f'Procesando {total} usuarios...')

        for i, user in enumerate(users, 1):
            actualizar_perfil(user)
            if i % 50 == 0:
                self.stdout.write(f'  Progreso: {i}/{total}')

        self.stdout.write(self.style.SUCCESS(f'✅ Perfiles actualizados para {total} usuarios'))
