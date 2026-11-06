from django.contrib import admin
from django.urls import path, include
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from mascotas.forms import LoginForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(
        template_name='mascotas/login.html', authentication_form=LoginForm, redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('cuenta/cambiar-contrasena/', auth_views.PasswordChangeView.as_view(
        template_name='mascotas/cambiar_contrasena.html',
        success_url=reverse_lazy('password_change_done')), name='password_change'),
    path('cuenta/cambiar-contrasena/listo/', auth_views.PasswordChangeDoneView.as_view(
        template_name='mascotas/cambiar_contrasena_lista.html'), name='password_change_done'),
    path('recuperar-contrasena/', auth_views.PasswordResetView.as_view(
        template_name='mascotas/recuperar_contrasena.html',
        email_template_name='mascotas/correo_recuperacion.txt',
        subject_template_name='mascotas/asunto_recuperacion.txt',
        success_url=reverse_lazy('password_reset_done')), name='password_reset'),
    path('recuperar-contrasena/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='mascotas/recuperar_enviado.html'), name='password_reset_done'),
    path('recuperar-contrasena/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='mascotas/recuperar_confirmar.html',
        success_url=reverse_lazy('password_reset_complete')), name='password_reset_confirm'),
    path('recuperar-contrasena/completa/', auth_views.PasswordResetCompleteView.as_view(
        template_name='mascotas/recuperar_completa.html'), name='password_reset_complete'),
    path('', include('mascotas.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
