from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Mascota, Adopcion


class RegistroForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class MascotaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'color', 'descripcion', 'foto',
                   'zona', 'estado', 'telefono_contacto', 'mostrar_telefono']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}


class AdopcionForm(forms.ModelForm):
    class Meta:
        model = Adopcion
        fields = ['nombre', 'especie', 'edad_aproximada', 'descripcion', 'foto', 'zona']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4})}