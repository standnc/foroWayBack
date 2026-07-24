from django.views.generic import TemplateView, ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.db.models import Count, Q
from .models import Categoria, Hilo, Post
from .forms import HiloForm, PostForm
from accounts.models import User


class IndexView(TemplateView):
    template_name = "forum/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorias"] = (
            Categoria.objects.annotate(
                total_hilos=Count("hilos", distinct=True),
                total_posts=Count("hilos__posts", distinct=True),
            ).order_by("nombre")
        )
        ctx["stats"] = [
            {"valor": Categoria.objects.count(), "etiqueta": "Categorías"},
            {"valor": Hilo.objects.count(), "etiqueta": "Hilos"},
            {"valor": Post.objects.count(), "etiqueta": "Posts"},
            {"valor": User.objects.count(), "etiqueta": "Usuarios"},
        ]
        return ctx


class CategoriaListView(ListView):
    model = Categoria
    template_name = "forum/categoria_list.html"
    context_object_name = "categorias"

    def get_queryset(self):
        return Categoria.objects.annotate(
            total_hilos=Count("hilos", distinct=True),
            total_posts=Count("hilos__posts", distinct=True),
        ).order_by("nombre")


class CategoriaDetailView(DetailView):
    model = Categoria
    template_name = "forum/categoria_detail.html"
    context_object_name = "categoria"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["hilos"] = (
            self.object.hilos.annotate(
                num_respuestas=Count("posts") - 1,
            )
            .select_related("autor")
            .order_by("-sticky", "-ultimo_post")
        )
        return ctx


class HiloDetailView(DetailView):
    model = Hilo
    template_name = "forum/hilo_detail.html"
    context_object_name = "hilo"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["posts"] = (
            self.object.posts.select_related("autor").order_by("orden")
        )
        ctx["form"] = PostForm()
        return ctx

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('account_login')}?next={request.path}")
        hilo = self.get_object()
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.hilo = hilo
            post.autor = request.user
            ultimo_orden = (
                Post.objects.filter(hilo=hilo).aggregate(max=Count("orden"))["max"] or 0
            )
            post.orden = ultimo_orden + 1
            post.save()
            hilo.ultimo_post = post.creado
            hilo.save(update_fields=["ultimo_post"])
            return redirect(f"{reverse('forum:hilo', kwargs={'pk': hilo.pk})}#post-{post.pk}")
        ctx = self.get_context_data(object=hilo)
        ctx["form"] = form
        return self.render_to_response(ctx)


class CrearHiloView(LoginRequiredMixin, CreateView):
    model = Hilo
    form_class = HiloForm
    template_name = "forum/crear_hilo.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        slug = self.kwargs.get("slug")
        if slug:
            kwargs["initial"] = {"categoria": get_object_or_404(Categoria, slug=slug)}
        return kwargs

    def form_valid(self, form):
        form.instance.autor = self.request.user
        response = super().form_valid(form)
        Post.objects.create(
            hilo=self.object,
            autor=self.request.user,
            contenido=form.cleaned_data["contenido_apertura"],
            orden=0,
        )
        return response

    def get_success_url(self):
        return reverse("forum:hilo", kwargs={"pk": self.object.pk})


class BuscarView(TemplateView):
    template_name = "forum/buscar.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        if query:
            results = Hilo.objects.filter(
                Q(titulo__icontains=query) |
                Q(autor_historico__icontains=query)
            ).select_related("categoria", "autor").order_by("-creado")[:30]
            ctx["resultados"] = results
        else:
            ctx["resultados"] = None
        return ctx


class PerfilView(DetailView):
    model = User
    template_name = "forum/perfil.html"
    context_object_name = "profile_user"
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_object(self):
        return User.objects.get(username=self.kwargs["username"])

