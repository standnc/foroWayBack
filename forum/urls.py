from django.urls import path
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
]
