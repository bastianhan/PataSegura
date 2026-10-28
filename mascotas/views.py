from django.shortcuts import render
from .models import Establecimiento
from .models import Adopcion

## Hace que se el inicio de la pagina sea funcional
def inicio(request):
    return render(request, 'mascotas/index.html')

## Lista de establecimientos funcional
def lista_establecimientos(request):
    establecimientos = Establecimiento.objects.all()
    return render(request, 'mascotas/establecimientos.html', {'establecimientos': establecimientos})

def lista_adopciones(request):
    adopciones = Adopcion.objects.all()
    return render(request, 'mascotas/adopciones.html', {'Adopciones': adopciones})
