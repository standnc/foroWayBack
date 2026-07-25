from django import forms
from .models import Hilo, Post, Report, Warning, Ban
from django.utils.html import strip_tags
from accounts.models import User


class HiloForm(forms.ModelForm):
    class Meta:
        model = Hilo
        fields = ("titulo", "categoria", "contenido_apertura")
        labels = {
            "titulo": "Título del hilo",
            "categoria": "Categoría",
            "contenido_apertura": "Mensaje",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white placeholder-slate-400 "
                         "focus:ring-2 focus:ring-boom focus:border-transparent",
                "placeholder": "Título de tu hilo...",
                "maxlength": "200",
            }),
            "categoria": forms.Select(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white focus:ring-2 focus:ring-boom focus:border-transparent",
            }),
            "contenido_apertura": forms.Textarea(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white placeholder-slate-400 "
                         "focus:ring-2 focus:ring-boom focus:border-transparent",
                "placeholder": "Escribe tu mensaje...",
                "rows": "8",
            }),
        }

    def clean_titulo(self):
        valor = self.cleaned_data["titulo"]
        if len(strip_tags(valor).strip()) < 3:
            raise forms.ValidationError("El título debe tener al menos 3 caracteres.")
        return valor

    def clean_contenido_apertura(self):
        valor = self.cleaned_data["contenido_apertura"]
        if len(strip_tags(valor).strip()) < 1:
            raise forms.ValidationError("El mensaje no puede estar vacío.")
        return valor


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("contenido",)
        labels = {
            "contenido": "Tu respuesta",
        }
        widgets = {
            "contenido": forms.Textarea(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white placeholder-slate-400 "
                         "focus:ring-2 focus:ring-boom focus:border-transparent",
                "placeholder": "Escribe tu respuesta...",
                "rows": "5",
            }),
        }

    def clean_contenido(self):
        valor = self.cleaned_data["contenido"]
        if len(strip_tags(valor).strip()) < 1:
            raise forms.ValidationError("La respuesta no puede estar vacía.")
        return valor


# ============ MODERATION FORMS ============

class ResolverReportForm(forms.Form):
    """Form to resolve a report with optional action."""
    ACCIONES = [
        ("ignorar", "Ignorar reporte"),
        ("advertir", "Advertir al usuario"),
        ("banear", "Banear al usuario"),
    ]
    accion = forms.ChoiceField(choices=ACCIONES, widget=forms.RadioSelect)
    nota = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                     "px-4 py-2 text-white placeholder-slate-400 "
                     "focus:ring-2 focus:ring-boom focus:border-transparent",
            "placeholder": "Nota interna (opcional)...",
            "rows": "3",
        }),
        required=False,
    )
    duracion_ban = forms.ChoiceField(
        choices=[
            ("1", "1 día"),
            ("7", "7 días"),
            ("30", "30 días"),
            ("permanente", "Permanente"),
        ],
        widget=forms.Select(attrs={
            "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                     "px-4 py-2 text-white focus:ring-2 focus:ring-boom focus:border-transparent",
        }),
        required=False,
        label="Duración del baneo",
    )


class WarningForm(forms.ModelForm):
    class Meta:
        model = Warning
        fields = ("usuario", "motivo")
        labels = {
            "usuario": "Usuario",
            "motivo": "Motivo de la advertencia",
        }
        widgets = {
            "usuario": forms.Select(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white focus:ring-2 focus:ring-boom focus:border-transparent",
            }),
            "motivo": forms.Textarea(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white placeholder-slate-400 "
                         "focus:ring-2 focus:ring-boom focus:border-transparent",
                "placeholder": "Describe el motivo de la advertencia...",
                "rows": "4",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = User.objects.filter(is_active=True).order_by("email")


class BanForm(forms.ModelForm):
    DURACIONES = [
        ("1", "1 día"),
        ("7", "7 días"),
        ("30", "30 días"),
        ("permanente", "Permanente"),
    ]
    duracion = forms.ChoiceField(choices=DURACIONES, label="Duración")

    class Meta:
        model = Ban
        fields = ("usuario", "motivo", "tipo")
        labels = {
            "usuario": "Usuario",
            "motivo": "Motivo del baneo",
            "tipo": "Tipo",
        }
        widgets = {
            "usuario": forms.Select(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white focus:ring-2 focus:ring-boom focus:border-transparent",
            }),
            "motivo": forms.Textarea(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white placeholder-slate-400 "
                         "focus:ring-2 focus:ring-boom focus:border-transparent",
                "placeholder": "Describe el motivo del baneo...",
                "rows": "4",
            }),
            "tipo": forms.Select(attrs={
                "class": "w-full rounded-lg bg-slate-800 border border-slate-600 "
                         "px-4 py-2 text-white focus:ring-2 focus:ring-boom focus:border-transparent",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = User.objects.filter(is_active=True).order_by("email")