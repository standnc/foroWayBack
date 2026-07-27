from django.urls import path
from . import views_auth
from . import views

app_name = "forum"

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("categorias/", views.CategoriaListView.as_view(), name="categorias"),
    path("categoria/<slug:slug>/", views.CategoriaDetailView.as_view(), name="categoria"),
    path("nuevo-hilo/", views.CrearHiloView.as_view(), name="crear_hilo"),
    path("nuevo-hilo/<slug:slug>/", views.CrearHiloView.as_view(), name="crear_hilo_en_categoria"),
    path("hilo/<int:pk>/", views.HiloDetailView.as_view(), name="hilo"),
    path("buscar/", views.BuscarView.as_view(), name="buscar"),
    path("perfil/<str:username>/", views.PerfilView.as_view(), name="perfil"),
    # Verificación (T6.3)
    path("cuenta/verificar/", views.VerifyWaitingView.as_view(), name="verify_waiting"),
    # Moderación
    path("moderacion/", views.ModerationPanelView.as_view(), name="moderation_panel"),
    path("moderacion/report/<int:pk>/resolver/", views.ResolverReportView.as_view(), name="resolver_report"),
    path("moderacion/warning/crear/", views.CrearWarningView.as_view(), name="crear_warning"),
    path("moderacion/ban/crear/", views.CrearBanView.as_view(), name="crear_ban"),
    path("moderacion/historial/", views.HistorialModeracionView.as_view(), name="historial_moderacion"),
    # Inline auth (HTMX)
    path("api/auth/login/", views_auth.InlineLoginView.as_view(), name="inline_login"),
    path("api/auth/signup/", views_auth.InlineSignupView.as_view(), name="inline_signup"),
]
