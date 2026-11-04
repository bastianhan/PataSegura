from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .forms import RegistroForm, MascotaForm, AdopcionForm
from .models import Mascota, Establecimiento, Adopcion


def inicio(request):
    return render(request, 'mascotas/index.html')


def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)  # lo loguea automáticamente apenas se registra
            return redirect('inicio')
    else:
        form = RegistroForm()
    return render(request, 'mascotas/registro.html', {'form': form})


def lista_mascotas_perdidas(request):
    mascotas = Mascota.objects.filter(estado='perdida').order_by('-fecha_publicacion')
    return render(request, 'mascotas/lista_perdidas.html', {'mascotas': mascotas})


def detalle_mascota(request, mascota_id):
    # get_object_or_404: trae el objeto, o muestra un 404 prolijo si no existe (en vez de romper)
    mascota = get_object_or_404(Mascota, id=mascota_id)
    return render(request, 'mascotas/detalle_mascota.html', {'mascota': mascota})


@login_required
def reportar_mascota(request):
    if request.method == 'POST':
        form = MascotaForm(request.POST, request.FILES)  # request.FILES: necesario para la foto
        if form.is_valid():
            reporte = form.save(commit=False)  # arma el objeto pero no lo guarda todavía
            reporte.usuario = request.user      # le asigna el dueño antes de guardar
            reporte.save()
            return redirect('lista_mascotas_perdidas')
    else:
        form = MascotaForm()
    return render(request, 'mascotas/reportar_mascota.html', {'form': form})


def lista_establecimientos(request):
    establecimientos = Establecimiento.objects.all()
    return render(request, 'mascotas/establecimientos.html', {'establecimientos': establecimientos})


def lista_adopciones(request):
    adopciones = Adopcion.objects.filter(disponible=True).order_by('-fecha_publicacion')
    return render(request, 'mascotas/adopciones.html', {'adopciones': adopciones})


@login_required
def publicar_adopcion(request):
    if request.method == 'POST':
        form = AdopcionForm(request.POST, request.FILES)
        if form.is_valid():
            publicacion = form.save(commit=False)
            publicacion.usuario = request.user
            publicacion.save()
            return redirect('lista_adopciones')
    else:
        form = AdopcionForm()
    return render(request, 'mascotas/publicar_adopcion.html', {'form': form})

@login_required
def mi_cuenta(request):
    mis_mascotas = request.user.mascotas_reportadas.all()
    mis_adopciones = request.user.mascotas_adopcion.all()
    return render(request, 'mascotas/mi_cuenta.html', {
        'mis_mascotas': mis_mascotas,
        'mis_adopciones': mis_adopciones,
    })