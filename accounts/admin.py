from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("email", "username", "is_staff", "is_active", "is_verified", "date_joined", "last_login")
    list_filter = ("is_staff", "is_active", "is_verified", "date_joined", "last_login")
    search_fields = ("email", "username")
    ordering = ("-date_joined",)
    date_hierarchy = "date_joined"
    readonly_fields = ("date_joined", "last_login")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Custom Fields", {
            "fields": ("bio", "firma", "avatar_url", "is_verified")
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Custom Fields", {
            "fields": ("email", "bio", "firma")
        }),
    )
