from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('registro/', views.registro, name='registro'),
    path('perdidas/', views.lista_mascotas_perdidas, name='lista_mascotas_perdidas'),
    path('perdidas/<int:mascota_id>/', views.detalle_mascota, name='detalle_mascota'),
    path('perdidas/reportar/', views.reportar_mascota, name='reportar_mascota'),
    path('establecimientos/', views.lista_establecimientos, name='lista_establecimientos'),
    path('adopciones/', views.lista_adopciones, name='lista_adopciones'),
    path('adopciones/publicar/', views.publicar_adopcion, name='publicar_adopcion'),
    path('cuenta/', views.mi_cuenta, name='mi_cuenta'),
]