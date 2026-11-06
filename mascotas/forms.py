import re

from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from .models import Mascota, Adopcion, ReportePerdida, PerfilUsuario
from .moderacion import censurar
from .validators import (validar_nombre_persona, validar_correo_real, procesar_foto,
                         validar_ubicacion_chile, limpiar_espacios)

REGEX_TELEFONO = r'^\+?[0-9 ()-]{8,20}$'


class CensuraMixin:
    """Caso 2.2: censura las palabras ofensivas de los campos de texto indicados
    y recuerda si hubo que censurar algo (para avisarle al usuario)."""
    campos_censurados = ()

    def _post_clean(self):
        self.fue_censurado = False
        for campo in self.campos_censurados:
            valor = self.cleaned_data.get(campo)
            if isinstance(valor, str):
                limpio = censurar(valor)
                if limpio != valor:
                    self.cleaned_data[campo] = limpio
                    self.fue_censurado = True
        super()._post_clean()


def _separar_nombre(nombre_completo):
    partes = nombre_completo.split()
    return (partes[0] if partes else ''), ' '.join(partes[1:])


# ---------------------------------------------------------------------
#  Registro e inicio de sesión
# ---------------------------------------------------------------------
class RegistroForm(UserCreationForm):
    """Crea la cuenta (datos_cuenta) y el perfil con los datos_contacto."""
    nombre_completo = forms.CharField(
        label='Nombre completo', max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Nombre completo', 'autocomplete': 'name'}),
    )
    email = forms.EmailField(
        label='Correo electrónico',
        error_messages={'invalid': 'Ingresa un correo electrónico válido (ejemplo: nombre@gmail.com).'},
        widget=forms.EmailInput(attrs={'placeholder': 'Correo electrónico', 'autocomplete': 'email'}),
    )
    telefono = forms.CharField(
        label='Teléfono (opcional)', max_length=30, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Teléfono de contacto (opcional)', 'autocomplete': 'tel'}),
    )

    class Meta:
        model = User
        fields = ['nombre_completo', 'email', 'telefono']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'placeholder': 'Contraseña (mínimo 8 caracteres)', 'autocomplete': 'new-password'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Confirmar contraseña', 'autocomplete': 'new-password'})
        self.fields['password2'].label = 'Confirmar contraseña'
        # 1.3: mensaje claro cuando se deja una casilla en blanco
        mensajes = {
            'nombre_completo': 'Escribe tu nombre completo.',
            'email': 'Escribe tu correo electrónico.',
            'password1': 'Escribe una contraseña.',
            'password2': 'Repite la contraseña.',
        }
        for campo, texto in mensajes.items():
            self.fields[campo].error_messages['required'] = texto
        self.error_messages['password_mismatch'] = 'Las contraseñas no coinciden. Escríbelas de nuevo.'  # 1.4

    def clean_nombre_completo(self):
        return validar_nombre_persona(self.cleaned_data['nombre_completo'])  # 1.1 y 1.2

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return validar_correo_real(email)  # 1.5

    def clean_telefono(self):
        telefono = limpiar_espacios(self.cleaned_data.get('telefono'))
        if telefono and not re.match(REGEX_TELEFONO, telefono):
            raise forms.ValidationError('El teléfono solo puede tener números, espacios y el signo +.')
        return telefono

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.username = self.cleaned_data['email']  # el correo sirve como nombre de usuario
        usuario.email = self.cleaned_data['email']
        usuario.first_name, usuario.last_name = _separar_nombre(self.cleaned_data['nombre_completo'])
        if commit:
            usuario.save()
            perfil = PerfilUsuario.de(usuario)
            perfil.telefono = self.cleaned_data.get('telefono', '')
            perfil.save()
        return usuario


class LoginForm(AuthenticationForm):
    """Login con correo electrónico (también acepta el nombre de usuario antiguo)."""
    username = forms.CharField(
        label='Correo electrónico',
        widget=forms.TextInput(attrs={'placeholder': 'Correo electrónico', 'autocomplete': 'email', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Contraseña', strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña', 'autocomplete': 'current-password'}),
    )
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Correo o contraseña incorrectos.',
    }

    def clean(self):
        """Después de varios intentos fallidos, bloquea ese correo un rato (evita adivinar contraseñas)."""
        correo = (self.cleaned_data.get('username') or '').strip().lower()
        clave = f'login-fallido:{correo}'
        maximo = settings.LIMITES['INTENTOS_LOGIN']
        minutos = settings.LIMITES['MINUTOS_BLOQUEO_LOGIN']
        if cache.get(clave, 0) >= maximo:
            raise forms.ValidationError(
                f'Demasiados intentos fallidos. Por seguridad, espera {minutos} minutos e inténtalo de nuevo.')
        try:
            datos = super().clean()
        except forms.ValidationError:
            cache.set(clave, cache.get(clave, 0) + 1, minutos * 60)
            raise
        cache.delete(clave)
        return datos


# ---------------------------------------------------------------------
#  Crear alerta = MascotaForm + ReporteForm (se muestran juntos)
# ---------------------------------------------------------------------
class MascotaForm(CensuraMixin, forms.ModelForm):
    campos_censurados = ('nombre', 'raza', 'color', 'descripcion', 'zona')

    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'color', 'descripcion', 'foto',
                  'zona', 'telefono_contacto', 'mostrar_telefono']
        labels = {
            'descripcion': 'Descripción',
            'zona': 'Referencia del lugar',
            'telefono_contacto': 'Teléfono de contacto',
            'mostrar_telefono': 'Mostrar mi teléfono en la publicación',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Max'}),
            'especie': forms.RadioSelect,
            'raza': forms.TextInput(attrs={'placeholder': 'Ej: Golden Retriever, quiltro…'}),
            'color': forms.TextInput(attrs={'placeholder': 'Ej: café con manchas blancas'}),
            'descripcion': forms.Textarea(attrs={
                'rows': 4, 'placeholder': 'Tamaño, collar, señas particulares, si es asustadizo…'}),
            'zona': forms.TextInput(attrs={'placeholder': 'Ej: Plaza Ñuñoa, cerca de la pileta'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }

    def __init__(self, *args, tipo='perdida', **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo = tipo
        # Si perdiste a tu mascota sabes su nombre; si la encontraste, quizás no.
        self.fields['nombre'].required = (tipo == 'perdida')
        self.fields['especie'].choices = [c for c in self.fields['especie'].choices if c[0]]
        self.fields['nombre'].error_messages['required'] = 'Ingresa el nombre de tu mascota.'
        self.fields['especie'].error_messages['required'] = 'Selecciona la especie.'
        self.fields['descripcion'].error_messages['required'] = 'Describe a la mascota.'
        self.fields['descripcion'].widget.attrs['maxlength'] = settings.LIMITES['LARGO_MAX_DESCRIPCION']
        self.fields['nombre'].widget.attrs['maxlength'] = 40
        self.fields['zona'].error_messages['required'] = 'Escribe una referencia del lugar (barrio, plaza, calle).'

    def clean_nombre(self):
        nombre = limpiar_espacios(self.cleaned_data.get('nombre'))
        if len(nombre) > 40:
            raise forms.ValidationError('El nombre es muy largo (máximo 40 caracteres).')
        return nombre

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        maximo = settings.LIMITES['LARGO_MAX_DESCRIPCION']
        if len(descripcion) < 10:
            raise forms.ValidationError('La descripción es muy corta (mínimo 10 caracteres).')
        if len(descripcion) > maximo:  # 2.5
            raise forms.ValidationError(
                f'La descripción es muy larga: tiene {len(descripcion)} caracteres y el límite es {maximo}.')
        return descripcion

    def clean_zona(self):
        zona = limpiar_espacios(self.cleaned_data.get('zona'))
        if not zona:
            raise forms.ValidationError(self.fields['zona'].error_messages['required'])
        return zona

    def clean_telefono_contacto(self):
        telefono = limpiar_espacios(self.cleaned_data.get('telefono_contacto'))
        if telefono and not re.match(REGEX_TELEFONO, telefono):
            raise forms.ValidationError('El teléfono solo puede tener números, espacios y el signo +.')
        return telefono

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and foto is not getattr(self.instance, 'foto', None) and hasattr(foto, 'content_type'):
            return procesar_foto(foto)  # 2.4: solo imágenes reales, sin metadatos
        return foto


class ReporteForm(forms.ModelForm):
    # Las coordenadas se llenan solas al hacer clic en el mapa (campos ocultos)
    _errores_ubicacion = {
        'required': 'Marca en el mapa dónde se vio por última vez.',
        'invalid': 'La ubicación no es válida. Marca un punto en el mapa.',
        'max_value': 'La ubicación no es válida. Marca un punto en el mapa.',
        'min_value': 'La ubicación no es válida. Marca un punto en el mapa.',
        'max_digits': 'La ubicación no es válida. Marca un punto en el mapa.',
        'max_decimal_places': 'La ubicación no es válida. Marca un punto en el mapa.',
        'max_whole_digits': 'La ubicación no es válida. Marca un punto en el mapa.',
    }
    latitud = forms.DecimalField(widget=forms.HiddenInput, max_digits=9, decimal_places=6,
                                 min_value=-90, max_value=90, error_messages=_errores_ubicacion)
    longitud = forms.DecimalField(widget=forms.HiddenInput, max_digits=9, decimal_places=6,
                                  min_value=-180, max_value=180, error_messages=_errores_ubicacion)

    def clean_latitud(self):
        return round(self.cleaned_data['latitud'], 6)

    def clean_longitud(self):
        return round(self.cleaned_data['longitud'], 6)

    class Meta:
        model = ReportePerdida
        fields = ['fecha_evento', 'latitud', 'longitud']
        widgets = {'fecha_evento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}

    def __init__(self, *args, tipo='perdida', **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_evento'].label = '¿Cuándo la encontraste?' if tipo == 'hallazgo' else '¿Cuándo se perdió?'
        self.fields['fecha_evento'].widget.attrs['max'] = timezone.localdate().isoformat()
        self.fields['fecha_evento'].error_messages['required'] = 'Indica la fecha.'

    def clean_fecha_evento(self):
        fecha = self.cleaned_data['fecha_evento']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha no puede ser futura.')
        return fecha

    def clean(self):
        datos = super().clean()
        # Mostramos un solo mensaje si falta o está mal la ubicación
        if 'longitud' in self.errors:
            if 'latitud' not in self.errors:
                self.add_error('latitud', 'La ubicación no es válida. Marca un punto en el mapa.')
            del self.errors['longitud']
        lat, lng = datos.get('latitud'), datos.get('longitud')
        if lat is not None and lng is not None:
            try:
                validar_ubicacion_chile(lat, lng)  # 3.3
            except forms.ValidationError as e:
                self.add_error('latitud', e)
        return datos


class AdopcionForm(CensuraMixin, forms.ModelForm):
    campos_censurados = ('nombre', 'edad_aproximada', 'descripcion', 'zona')

    class Meta:
        model = Adopcion
        fields = ['nombre', 'especie', 'edad_aproximada', 'descripcion', 'foto', 'zona']
        labels = {'descripcion': 'Descripción', 'edad_aproximada': 'Edad aproximada', 'zona': 'Zona'}
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000}),
                   'foto': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'})}

    def clean_descripcion(self):
        descripcion = self.cleaned_data['descripcion'].strip()
        if len(descripcion) > settings.LIMITES['LARGO_MAX_DESCRIPCION']:
            raise forms.ValidationError(f'La descripción es muy larga (máximo {settings.LIMITES["LARGO_MAX_DESCRIPCION"]} caracteres).')
        return descripcion

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'content_type'):
            return procesar_foto(foto)
        return foto


# ---------------------------------------------------------------------
#  Mi cuenta → Configuración (editar datos de contacto)
# ---------------------------------------------------------------------
class PerfilForm(forms.ModelForm):
    nombre_completo = forms.CharField(label='Nombre completo', max_length=150)

    class Meta:
        model = PerfilUsuario
        fields = ['nombre_completo', 'telefono', 'comuna', 'mostrar_telefono']
        labels = {'telefono': 'Teléfono', 'comuna': 'Comuna', 'mostrar_telefono': 'Mostrar mi teléfono en mis publicaciones'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre_completo'].initial = self.instance.usuario.get_full_name()

    def clean_nombre_completo(self):
        return validar_nombre_persona(self.cleaned_data['nombre_completo'])

    def clean_telefono(self):
        telefono = limpiar_espacios(self.cleaned_data.get('telefono'))
        if telefono and not re.match(REGEX_TELEFONO, telefono):
            raise forms.ValidationError('El teléfono solo puede tener números, espacios y el signo +.')
        return telefono

    def clean_comuna(self):
        comuna = censurar(limpiar_espacios(self.cleaned_data.get('comuna')))
        return comuna[:80]

    def save(self, commit=True):
        perfil = super().save(commit=False)
        usuario = perfil.usuario
        usuario.first_name, usuario.last_name = _separar_nombre(self.cleaned_data['nombre_completo'])
        if commit:
            usuario.save()
            perfil.save()
        return perfil
