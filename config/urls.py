from django.contrib import admin
from django.urls import include, path

from forum.admin_logs import log_view

urlpatterns = [
    # Antes de admin/: AdminSite tiene un catch-all final que se traga
    # cualquier ruta bajo admin/ declarada después y devuelve 404.
    path("admin/logs/", log_view, name="admin_log_view"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("forum.urls")),
]

