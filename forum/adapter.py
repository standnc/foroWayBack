from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class ForumAccountAdapter(DefaultAccountAdapter):
    def generate_unique_username(self, email):
        base = email.split("@")[0][:30]
        username = base
        while User.objects.filter(username=username).exists():
            import random
            username = f"{base}_{random.randint(1000, 9999)}"
        return username

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.username:
            user.username = self.generate_unique_username(user.email)
        if commit:
            user.save()
        return user
