from django.contrib import admin
from django.urls import path, include
from forum.admin_logs import log_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("admin/logs/", log_view, name="admin_log_view"),
    path("accounts/", include("allauth.urls")),
    path("", include("forum.urls")),
]

