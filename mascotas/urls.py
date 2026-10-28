from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('establecimientos/', views.lista_establecimientos, name='lista_establecimientos'),
    path('adopciones/', views.lista_adopciones, name='lista_adopciones'),
]