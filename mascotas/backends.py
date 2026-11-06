from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class CorreoOUsuarioBackend(ModelBackend):
    """Permite iniciar sesión escribiendo el correo electrónico
    (o el nombre de usuario, para cuentas creadas antes del cambio)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        texto = username.strip()
        usuario = (User.objects.filter(username__iexact=texto).first()
                   or User.objects.filter(email__iexact=texto).order_by('id').first())
        if usuario is None:
            User().set_password(password)  # mismo tiempo de respuesta exista o no la cuenta
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
