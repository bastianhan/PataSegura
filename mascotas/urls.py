from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),

    # Foro principal (mascotas perdidas) + crear alerta
    path('perdidas/', views.lista_mascotas_perdidas, name='lista_mascotas_perdidas'),
    path('perdidas/<int:mascota_id>/', views.detalle_mascota, name='detalle_mascota'),
    path('perdidas/<int:mascota_id>/estado/', views.cambiar_estado, name='cambiar_estado'),
    path('perdidas/<int:mascota_id>/editar/', views.editar_reporte, name='editar_reporte'),
    path('perdidas/<int:mascota_id>/denunciar/', views.denunciar, name='denunciar'),
    path('perdidas/reportar/', views.reportar_mascota, name='reportar_mascota'),

    # Mapa interactivo (+ datos en JSON para los pines)
    path('mapa/', views.mapa, name='mapa'),
    path('api/reportes/', views.api_reportes, name='api_reportes'),

    # Foros secundarios
    path('hallazgos/', views.lista_hallazgos, name='lista_hallazgos'),
    path('adopciones/', views.lista_adopciones, name='lista_adopciones'),
    path('adopciones/publicar/', views.publicar_adopcion, name='publicar_adopcion'),
    path('establecimientos/', views.lista_establecimientos, name='lista_establecimientos'),

    # Chats
    path('chats/', views.lista_chats, name='lista_chats'),
    path('chats/<int:conv_id>/', views.chat_detalle, name='chat_detalle'),
    path('chats/<int:conv_id>/mensajes/', views.api_mensajes, name='api_mensajes'),
    path('perdidas/<int:mascota_id>/contactar/', views.iniciar_chat, name='iniciar_chat'),

    # Mi cuenta
    path('cuenta/', views.mi_cuenta, name='mi_cuenta'),
    path('cuenta/publicaciones/', views.mis_publicaciones, name='mis_publicaciones'),
    path('cuenta/configuracion/', views.configuracion, name='configuracion'),
]
