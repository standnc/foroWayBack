from django.views.generic import TemplateView, ListView, DetailView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import Categoria, Hilo, Post, Report, Warning, Ban, ModerationLog
from .forms import HiloForm, PostForm, ResolverReportForm, WarningForm, BanForm
from accounts.models import User


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin: solo staff/superuser pueden acceder."""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser


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


# ============ MODERATION VIEWS ============

class ModerationPanelView(StaffRequiredMixin, TemplateView):
    template_name = "forum/moderation/panel.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.now()
        inicio_hoy = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
        inicio_semana = inicio_hoy - timedelta(days=hoy.weekday())
        inicio_mes = inicio_hoy.replace(day=1)

        ctx["reportes_pendientes"] = Report.objects.filter(
            estado__in=["pendiente", "revisando"]
        ).select_related("post", "hilo", "reportado_por").order_by("-creado")

        ctx["total_warnings"] = Warning.objects.count()
        ctx["total_bans_activos"] = Ban.objects.filter(activo=True).count()

        ctx["ultimas_acciones"] = ModerationLog.objects.select_related(
            "moderador"
        ).order_by("-creado")[:20]

        ctx["stats"] = {
            "reportes_hoy": Report.objects.filter(creado__gte=inicio_hoy).count(),
            "reportes_semana": Report.objects.filter(creado__gte=inicio_semana).count(),
            "reportes_mes": Report.objects.filter(creado__gte=inicio_mes).count(),
            "pendientes": Report.objects.filter(estado="pendiente").count(),
            "warnings": ctx["total_warnings"],
            "bans_activos": ctx["total_bans_activos"],
        }
        return ctx


class ResolverReportView(StaffRequiredMixin, FormView):
    template_name = "forum/moderation/resolver_report.html"
    form_class = ResolverReportForm

    def dispatch(self, request, *args, **kwargs):
        self.report = get_object_or_404(Report, pk=self.kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["report"] = self.report
        return ctx

    def form_valid(self, form):
        accion = form.cleaned_data["accion"]
        nota = form.cleaned_data["nota"]

        self.report.estado = "resuelto"
        self.report.resuelto_por = self.request.user
        self.report.resuelto_en = timezone.now()
        self.report.nota_moderacion = nota
        self.report.save()

        target_user = None
        if self.report.post and self.report.post.autor:
            target_user = self.report.post.autor
        elif self.report.hilo and self.report.hilo.autor:
            target_user = self.report.hilo.autor

        if accion == "advertir" and target_user:
            Warning.objects.create(
                usuario=target_user,
                moderador=self.request.user,
                motivo=nota or "Advertencia por reporte #{}".format(self.report.pk),
            )

        if accion == "banear" and target_user:
            duracion = form.cleaned_data.get("duracion_ban", "permanente")
            dias = None if duracion == "permanente" else int(duracion)
            Ban.objects.create(
                usuario=target_user,
                moderador=self.request.user,
                motivo=nota or "Baneo por reporte #{}".format(self.report.pk),
                tipo="permanente" if duracion == "permanente" else "temporal",
                activo=True,
                expira=(timezone.now() + timedelta(days=dias)) if dias else None,
            )

        ModerationLog.objects.create(
            moderador=self.request.user,
            accion="resolver_reporte",
            descripcion="Reporte #{} resuelto: {}".format(self.report.pk, accion),
            target_post=self.report.post,
            target_hilo=self.report.hilo,
            target_usuario=target_user,
        )

        return redirect(reverse("forum:moderation_panel"))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class CrearWarningView(StaffRequiredMixin, CreateView):
    model = Warning
    form_class = WarningForm
    template_name = "forum/moderation/warning_form.html"
    success_url = reverse_lazy("forum:moderation_panel")

    def form_valid(self, form):
        form.instance.moderador = self.request.user
        response = super().form_valid(form)
        ModerationLog.objects.create(
            moderador=self.request.user,
            accion="advertir",
            descripcion="Advertencia a {}: {}".format(
                form.instance.usuario.email, form.instance.motivo[:100]
            ),
            target_usuario=form.instance.usuario,
        )
        return response


class CrearBanView(StaffRequiredMixin, CreateView):
    model = Ban
    form_class = BanForm
    template_name = "forum/moderation/ban_form.html"
    success_url = reverse_lazy("forum:moderation_panel")

    def form_valid(self, form):
        form.instance.moderador = self.request.user
        duracion = form.cleaned_data["duracion"]
        if duracion == "permanente":
            form.instance.tipo = "permanente"
            form.instance.expira = None
        else:
            form.instance.tipo = "temporal"
            form.instance.expira = timezone.now() + timedelta(days=int(duracion))
        response = super().form_valid(form)
        ModerationLog.objects.create(
            moderador=self.request.user,
            accion="banear",
            descripcion="Ban {} a {}: {}".format(
                form.instance.tipo, form.instance.usuario.email, form.instance.motivo[:100]
            ),
            target_usuario=form.instance.usuario,
        )
        return response


class HistorialModeracionView(StaffRequiredMixin, ListView):
    model = ModerationLog
    template_name = "forum/moderation/historial.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        return ModerationLog.objects.select_related(
            "moderador", "target_usuario"
        ).order_by("-creado")