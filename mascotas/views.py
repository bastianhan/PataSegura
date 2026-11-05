import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import limites
from .forms import RegistroForm, MascotaForm, AdopcionForm, ReporteForm, PerfilForm
from .models import (Mascota, Establecimiento, Adopcion, ReportePerdida, PerfilUsuario,
                     Conversacion, Mensaje, Denuncia)
from .moderacion import censurar

MENSAJE_SIN_ACCESO = 'No tienes acceso a esta publicación. Solo quien la creó puede modificarla.'


# =====================================================================
#  1. INICIO, REGISTRO (el login usa la vista de Django, ver core/urls.py)
# =====================================================================
def inicio(request):
    # La página de inicio es el login; si ya entraste, vas directo al mapa.
    return redirect('mapa' if request.user.is_authenticated else 'login')


def registro(request):
    if request.user.is_authenticated:
        return redirect('mapa')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            # lo loguea automáticamente apenas se registra
            login(request, usuario, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f'¡Bienvenido/a a PataSegura, {usuario.first_name}! 🐾')
            return redirect('mapa')
    else:
        form = RegistroForm()
    return render(request, 'mascotas/registro.html', {'form': form})


# =====================================================================
#  2. FUNCIONALIDAD CORAZÓN: FORO DE MASCOTAS PERDIDAS
# =====================================================================
def _feed(request, tipo):
    """Lista cronológica de reportes activos (sirve para perdidas y hallazgos)."""
    especie = request.GET.get('especie', 'todos')
    reportes = (ReportePerdida.objects
                .filter(tipo=tipo, estado_busqueda='activa')
                .select_related('mascota', 'mascota__usuario'))
    if especie in ('perro', 'gato', 'otro'):
        reportes = reportes.filter(mascota__especie=especie)
    else:
        especie = 'todos'
    # Paginación: aunque haya miles de alertas, cada página carga solo 10
    pagina = Paginator(reportes, 10).get_page(request.GET.get('pagina'))
    return render(request, 'mascotas/foro.html', {
        'reportes': pagina,
        'pagina': pagina,
        'tipo': tipo,
        'especie': especie,
        'nueva': request.GET.get('nueva', ''),
    })


def lista_mascotas_perdidas(request):
    return _feed(request, 'perdida')


def lista_hallazgos(request):
    return _feed(request, 'hallazgo')


def detalle_mascota(request, mascota_id):
    # get_object_or_404: trae el objeto, o muestra un 404 prolijo si no existe (en vez de romper)
    mascota = get_object_or_404(Mascota.objects.select_related('usuario'), id=mascota_id)
    reporte = ReportePerdida.objects.filter(mascota=mascota).first()
    conversacion = None
    if reporte and request.user.is_authenticated:
        conversacion = Conversacion.objects.filter(reporte=reporte, interesado=request.user).first()
    return render(request, 'mascotas/detalle_mascota.html', {
        'mascota': mascota,
        'reporte': reporte,
        'es_mia': request.user.is_authenticated and mascota.usuario_id == request.user.id,
        'conversacion': conversacion,
        'perfil_autor': PerfilUsuario.de(mascota.usuario),
    })


def _nuevo_token(request):
    """Caso 3.4: cada formulario lleva un código de un solo uso.
    Si alguien aprieta "Publicar" muchas veces, solo el primer envío se guarda."""
    token = secrets.token_urlsafe(16)
    tokens = request.session.get('tokens_alerta', [])[-9:]
    request.session['tokens_alerta'] = tokens + [token]
    return token


def _usar_token(request, token):
    tokens = request.session.get('tokens_alerta', [])
    if token and token in tokens:
        tokens.remove(token)
        request.session['tokens_alerta'] = tokens
        return True
    return False


@login_required  # Solo usuarios autenticados pueden crear reportes
def reportar_mascota(request):
    """Formulario "Crear Alerta". Guarda la MASCOTA y su REPORTE DE PÉRDIDA."""
    tipo = 'hallazgo' if request.POST.get('tipo', request.GET.get('tipo')) == 'hallazgo' else 'perdida'
    destino = 'lista_hallazgos' if tipo == 'hallazgo' else 'lista_mascotas_perdidas'
    bloqueo = limites.bloqueo_alertas(request.user)  # 2.1 y 3.1

    if request.method == 'POST':
        token = request.POST.get('token', '')
        if token not in request.session.get('tokens_alerta', []) or cache.get(f'token-usado:{token}'):
            # 3.4: envío repetido (doble clic, botón "atrás" + reenviar, etc.)
            messages.warning(request, 'Esta alerta ya fue enviada. No la publicamos dos veces.')
            return redirect(destino)

        form_mascota = MascotaForm(request.POST, request.FILES, tipo=tipo)  # request.FILES: necesario para la foto
        form_reporte = ReporteForm(request.POST, tipo=tipo)
        # Validamos los dos formularios (sin cortar en el primero) para mostrar TODOS los errores
        mascota_ok = form_mascota.is_valid()
        reporte_ok = form_reporte.is_valid()

        if bloqueo:
            messages.error(request, bloqueo)
        elif mascota_ok and reporte_ok:
            # Candado por usuario: si llegan varios envíos AL MISMO TIEMPO (doble clic, script),
            # solo uno pasa a la vez y los demás vuelven a revisar los límites después.
            candado = f'publicando:{request.user.id}'
            if not cache.add(candado, True, 15):
                messages.warning(request, 'Ya estamos publicando tu alerta, espera un momento.')
                return redirect(destino)
            try:
                bloqueo = limites.bloqueo_alertas(request.user)
                duplicada = limites.alerta_duplicada(request.user, tipo, form_mascota.cleaned_data)  # 3.2
                if bloqueo:
                    messages.error(request, bloqueo)
                    return redirect(destino)
                if duplicada:
                    form_mascota.add_error(None, 'Ya tienes una alerta activa igual a esta.')
                    messages.warning(request, 'Ya existe una alerta igual publicada por ti. No es necesario repetirla.')
                    return render(request, 'mascotas/reportar_mascota.html', {
                        'form': form_mascota, 'form_reporte': form_reporte, 'tipo': tipo,
                        'errores': [], 'duplicada': duplicada, 'token': token,
                    })
                # 3.4: el código del formulario se marca como usado (operación atómica)
                if not cache.add(f'token-usado:{token}', True, 24 * 3600) or not _usar_token(request, token):
                    messages.warning(request, 'Esta alerta ya fue enviada. No la publicamos dos veces.')
                    return redirect(destino)
                with transaction.atomic():  # se guardan los dos o ninguno
                    mascota = form_mascota.save(commit=False)  # arma el objeto pero no lo guarda todavía
                    mascota.usuario = request.user              # le asigna el dueño antes de guardar
                    mascota.save()
                    reporte = form_reporte.save(commit=False)
                    reporte.mascota = mascota
                    reporte.tipo = tipo
                    reporte.save()
            finally:
                cache.delete(candado)
            messages.success(request, '¡Hallazgo publicado!' if tipo == 'hallazgo'
                             else '¡Alerta publicada! Ya está visible en el foro y en el mapa.')
            if form_mascota.fue_censurado:  # 2.2
                messages.warning(request, 'Algunas palabras no permitidas fueron censuradas con ***.')
            return redirect(f'{reverse(destino)}?nueva={mascota.id}#m-{mascota.id}')
        else:
            messages.error(request, 'Faltan datos obligatorios. Complétalos para publicar la alerta.')
    else:
        perfil = PerfilUsuario.de(request.user)
        form_mascota = MascotaForm(tipo=tipo, initial={
            'telefono_contacto': perfil.telefono, 'mostrar_telefono': perfil.mostrar_telefono})
        form_reporte = ReporteForm(tipo=tipo, initial={'fecha_evento': timezone.localdate()})
        token = _nuevo_token(request)

    errores = [e for f in (form_mascota, form_reporte) for lista in f.errors.values() for e in lista]
    return render(request, 'mascotas/reportar_mascota.html', {
        'form': form_mascota,
        'form_reporte': form_reporte,
        'tipo': tipo,
        'errores': errores,
        'bloqueo': bloqueo,
        'token': token,
    })


def _reporte_propio(request, mascota_id):
    """Caso 3.5: trae el reporte solo si es del usuario; si no, muestra "no tienes acceso"."""
    reporte = get_object_or_404(ReportePerdida.objects.select_related('mascota'), mascota_id=mascota_id)
    if reporte.mascota.usuario_id != request.user.id:
        raise PermissionDenied(MENSAJE_SIN_ACCESO)
    return reporte


@login_required
def editar_reporte(request, mascota_id):
    """Editar una alerta propia (por ejemplo, corregir la ubicación)."""
    reporte = _reporte_propio(request, mascota_id)
    mascota = reporte.mascota
    if request.method == 'POST':
        form_mascota = MascotaForm(request.POST, request.FILES, instance=mascota, tipo=reporte.tipo)
        form_reporte = ReporteForm(request.POST, instance=reporte, tipo=reporte.tipo)
        mascota_ok = form_mascota.is_valid()
        reporte_ok = form_reporte.is_valid()
        if mascota_ok and reporte_ok:
            if limites.alerta_duplicada(request.user, reporte.tipo, form_mascota.cleaned_data, excluir_id=mascota.id):
                messages.warning(request, 'Ya tienes otra alerta activa igual a esta.')
            else:
                with transaction.atomic():
                    form_mascota.save()
                    form_reporte.save()
                messages.success(request, 'Publicación actualizada.')
                if form_mascota.fue_censurado:
                    messages.warning(request, 'Algunas palabras no permitidas fueron censuradas con ***.')
                return redirect('detalle_mascota', mascota_id=mascota.id)
        else:
            messages.error(request, 'Faltan datos obligatorios. Revisa los campos marcados en rojo.')
    else:
        form_mascota = MascotaForm(instance=mascota, tipo=reporte.tipo)
        form_reporte = ReporteForm(instance=reporte, tipo=reporte.tipo)

    errores = [e for f in (form_mascota, form_reporte) for lista in f.errors.values() for e in lista]
    return render(request, 'mascotas/reportar_mascota.html', {
        'form': form_mascota, 'form_reporte': form_reporte, 'tipo': reporte.tipo,
        'errores': errores, 'editando': mascota,
    })


@login_required
@require_POST
def denunciar(request, mascota_id):
    """Caso 2.4: denunciar una foto o texto indebido. Con varias denuncias la foto se oculta sola."""
    reporte = get_object_or_404(ReportePerdida.objects.select_related('mascota'), mascota_id=mascota_id)
    if reporte.mascota.usuario_id == request.user.id:
        messages.info(request, 'No puedes denunciar tu propia publicación.')
        return redirect('detalle_mascota', mascota_id=mascota_id)
    motivo = request.POST.get('motivo')
    if motivo not in dict(Denuncia.MOTIVOS):
        motivo = 'foto'
    try:
        with transaction.atomic():
            Denuncia.objects.create(reporte=reporte, usuario=request.user, motivo=motivo)
    except IntegrityError:
        messages.info(request, 'Ya habías denunciado esta publicación. La revisaremos.')
        return redirect('detalle_mascota', mascota_id=mascota_id)

    total = reporte.denuncias.filter(revisada=False).count()
    if total >= limites.limite('DENUNCIAS_PARA_OCULTAR') and reporte.mascota.foto:
        Mascota.objects.filter(id=mascota_id).update(foto_oculta=True)
    messages.success(request, 'Gracias por avisar. Revisaremos la publicación.')
    return redirect('detalle_mascota', mascota_id=mascota_id)


@login_required
@require_POST
def cambiar_estado(request, mascota_id):
    reporte = _reporte_propio(request, mascota_id)  # 3.5: si no es tuyo → "no tienes acceso"
    nuevo = request.POST.get('estado_busqueda')
    if nuevo in dict(ReportePerdida.ESTADOS):
        reporte.estado_busqueda = nuevo
        reporte.save(update_fields=['estado_busqueda'])
        if nuevo == 'encontrada':
            messages.success(request, '¡Qué buena noticia! 🎉 Marcamos la publicación como encontrada.')
        else:
            messages.success(request, f'Estado actualizado: {reporte.get_estado_busqueda_display()}.')
    volver = request.POST.get('volver', '')
    if not volver.startswith('/') or volver.startswith('//'):  # solo redirecciones dentro del sitio
        volver = reverse('detalle_mascota', args=[mascota_id])
    return redirect(volver)


# =====================================================================
#  3. MAPA INTERACTIVO
# =====================================================================
def mapa(request):
    return render(request, 'mascotas/mapa.html')


def api_reportes(request):
    """Datos en JSON para dibujar los pines del mapa (los lee static/mascotas/mapa.js)."""
    reportes = (ReportePerdida.objects
                .filter(estado_busqueda='activa', latitud__isnull=False, longitud__isnull=False)
                .select_related('mascota')[:3000])  # tope de seguridad
    datos = []
    for r in reportes:
        m = r.mascota
        datos.append({
            'id': m.id,
            'tipo': r.tipo,
            'estado_busqueda': r.estado_busqueda,
            'coordenadas': r.coordenadas,
            'nombre': m.nombre or 'Sin nombre',
            'especie': m.especie,
            'especie_texto': m.get_especie_display(),
            'raza': m.raza,
            'zona': m.zona,
            'foto': m.foto.url if m.foto_visible else None,
            'fecha_evento': r.fecha_evento.isoformat(),
            'dias': r.dias_desde_evento,
            'url': reverse('detalle_mascota', args=[m.id]),
        })
    return JsonResponse({'reportes': datos})


# =====================================================================
#  4. FOROS SECUNDARIOS: ADOPCIONES Y ESTABLECIMIENTOS
# =====================================================================
def lista_establecimientos(request):
    establecimientos = Establecimiento.objects.all()
    return render(request, 'mascotas/establecimientos.html', {'establecimientos': establecimientos})


def lista_adopciones(request):
    adopciones = Adopcion.objects.filter(disponible=True).order_by('-fecha_publicacion')
    refugios = Establecimiento.objects.filter(tipo='refugio')
    return render(request, 'mascotas/adopciones.html', {'adopciones': adopciones, 'refugios': refugios})


@login_required
def publicar_adopcion(request):
    bloqueo = limites.bloqueo_adopciones(request.user)
    if request.method == 'POST':
        form = AdopcionForm(request.POST, request.FILES)
        if bloqueo:
            messages.error(request, bloqueo)
        elif form.is_valid():
            publicacion = form.save(commit=False)
            publicacion.usuario = request.user
            publicacion.save()
            messages.success(request, 'Publicación de adopción creada.')
            if form.fue_censurado:
                messages.warning(request, 'Algunas palabras no permitidas fueron censuradas con ***.')
            return redirect('lista_adopciones')
    else:
        form = AdopcionForm()
    return render(request, 'mascotas/publicar_adopcion.html', {'form': form, 'bloqueo': bloqueo})


# =====================================================================
#  5. CHATS
# =====================================================================
def _mis_conversaciones(usuario):
    return (Conversacion.objects
            .filter(Q(interesado=usuario) | Q(reporte__mascota__usuario=usuario))
            .select_related('reporte__mascota__usuario', 'interesado')
            .distinct())


@login_required
def lista_chats(request):
    chats = []
    for conv in _mis_conversaciones(request.user):
        chats.append({
            'conv': conv,
            'otro': conv.otro(request.user),
            'mascota': conv.reporte.mascota,
            'ultimo': conv.mensajes.last(),
            'no_leidos': conv.mensajes.filter(leido=False).exclude(autor=request.user).count(),
        })
    return render(request, 'mascotas/chats.html', {'chats': chats})


@login_required
@require_POST
def iniciar_chat(request, mascota_id):
    reporte = get_object_or_404(ReportePerdida, mascota_id=mascota_id)
    if reporte.mascota.usuario_id == request.user.id:
        messages.info(request, 'Esta publicación es tuya.')
        return redirect('detalle_mascota', mascota_id=mascota_id)
    conv, _ = Conversacion.objects.get_or_create(reporte=reporte, interesado=request.user)
    return redirect('chat_detalle', conv_id=conv.id)


def _conversacion_de(request, conv_id):
    conv = get_object_or_404(Conversacion.objects.select_related('reporte__mascota__usuario', 'interesado'), id=conv_id)
    if not conv.participa(request.user):
        raise PermissionDenied('No tienes acceso a esta conversación.')  # 3.5
    return conv


def _mensaje_json(m, usuario):
    return {
        'id': m.id,
        'texto': m.texto,
        'mio': m.autor_id == usuario.id,
        'hora': timezone.localtime(m.fecha).strftime('%H:%M'),
        'leido': m.leido,
    }


@login_required
def chat_detalle(request, conv_id):
    conv = _conversacion_de(request, conv_id)

    if request.method == 'POST':
        texto = request.POST.get('texto', '').strip()
        es_fetch = request.headers.get('x-requested-with') == 'fetch'
        maximo = limites.limite('LARGO_MAX_MENSAJE')

        error, estado = None, 400
        if not texto:
            error = 'No escribiste nada. El mensaje está en blanco y no se envió.'  # 2.3
        elif len(texto) > maximo:
            error = f'El mensaje es muy largo: tiene {len(texto)} caracteres y el límite es {maximo}.'  # 2.5
        else:
            error = limites.bloqueo_mensajes(request.user)  # 2.1
            estado = 429

        if error:
            if es_fetch:
                return JsonResponse({'error': error}, status=estado)
            messages.error(request, error)
            return redirect('chat_detalle', conv_id=conv.id)

        limpio = censurar(texto)  # 2.2
        m = Mensaje.objects.create(conversacion=conv, autor=request.user, texto=limpio)
        conv.save(update_fields=['actualizada'])
        aviso = 'Algunas palabras no permitidas fueron censuradas.' if limpio != texto else None
        if es_fetch:
            return JsonResponse({'mensaje': _mensaje_json(m, request.user), 'aviso': aviso}, status=201)
        if aviso:
            messages.warning(request, aviso)
        return redirect('chat_detalle', conv_id=conv.id)

    conv.mensajes.filter(leido=False).exclude(autor=request.user).update(leido=True)
    return render(request, 'mascotas/chat.html', {
        'conv': conv,
        'otro': conv.otro(request.user),
        'mascota': conv.reporte.mascota,
        'mensajes': conv.mensajes.all(),
        'largo_max': limites.limite('LARGO_MAX_MENSAJE'),
    })


@login_required
def api_mensajes(request, conv_id):
    """Mensajes nuevos de un chat (el navegador pregunta cada pocos segundos)."""
    conv = _conversacion_de(request, conv_id)
    desde = request.GET.get('desde', '0')
    nuevos = conv.mensajes.filter(id__gt=int(desde) if desde.isdigit() and len(desde) < 12 else 0)[:200]
    respuesta = [_mensaje_json(m, request.user) for m in nuevos]
    ids = [m['id'] for m in respuesta]
    conv.mensajes.filter(id__in=ids, leido=False).exclude(autor=request.user).update(leido=True)
    return JsonResponse({'mensajes': respuesta})


# =====================================================================
#  6. MI CUENTA
# =====================================================================
@login_required
def mi_cuenta(request):
    return render(request, 'mascotas/mi_cuenta.html', {
        'perfil': PerfilUsuario.de(request.user),
        'total_publicaciones': request.user.mascotas_reportadas.count() + request.user.mascotas_adopcion.count(),
        'total_chats': _mis_conversaciones(request.user).count(),
    })


@login_required
def mis_publicaciones(request):
    mis_reportes = (ReportePerdida.objects.filter(mascota__usuario=request.user)
                    .select_related('mascota'))
    mis_adopciones = request.user.mascotas_adopcion.all()
    return render(request, 'mascotas/mis_publicaciones.html', {
        'mis_reportes': mis_reportes,
        'mis_adopciones': mis_adopciones,
    })


@login_required
def configuracion(request):
    perfil = PerfilUsuario.de(request.user)
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos de contacto actualizados.')
            return redirect('mi_cuenta')
    else:
        form = PerfilForm(instance=perfil)
    return render(request, 'mascotas/configuracion.html', {'form': form})
