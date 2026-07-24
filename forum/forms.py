from django import forms
from .models import Hilo, Post
from django.utils.html import strip_tags


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
