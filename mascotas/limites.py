"""
limites.py — Reglas anti-spam  (casos 2.1, 3.1 y 3.2 del plan de pruebas)
Cada función devuelve None si se puede continuar, o un texto explicando por qué no.
Los conteos se hacen con la base de datos, así funcionan aunque reinicies el servidor.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .moderacion import normalizar


def limite(nombre):
    return settings.LIMITES[nombre]


def _texto_espera(segundos):
    segundos = max(1, int(segundos))
    if segundos < 60:
        return f'{segundos} segundos'
    minutos = -(-segundos // 60)
    if minutos < 60:
        return f'{minutos} minuto{"s" if minutos != 1 else ""}'
    horas = -(-minutos // 60)
    return f'{horas} hora{"s" if horas != 1 else ""}'


def bloqueo_alertas(usuario):
    """2.1 y 3.1: ¿puede este usuario publicar otra alerta ahora?"""
    from .models import ReportePerdida

    ahora = timezone.now()
    mias = ReportePerdida.objects.filter(mascota__usuario=usuario)

    ultima = mias.order_by('-fecha_publicacion').values_list('fecha_publicacion', flat=True).first()
    espera = limite('SEGUNDOS_ENTRE_ALERTAS')
    if ultima and (ahora - ultima).total_seconds() < espera:
        falta = espera - (ahora - ultima).total_seconds()
        return f'Acabas de publicar una alerta. Espera {_texto_espera(falta)} antes de publicar otra.'

    hace_un_dia = ahora - timedelta(days=1)
    recientes = mias.filter(fecha_publicacion__gte=hace_un_dia).order_by('fecha_publicacion')
    if recientes.count() >= limite('ALERTAS_POR_DIA'):
        primera = recientes.values_list('fecha_publicacion', flat=True).first()
        falta = (primera + timedelta(days=1) - ahora).total_seconds()
        return (f'Llegaste al máximo de {limite("ALERTAS_POR_DIA")} alertas por día. '
                f'Podrás publicar otra en {_texto_espera(falta)}.')

    if mias.filter(estado_busqueda='activa').count() >= limite('ALERTAS_ACTIVAS_MAX'):
        return (f'Tienes {limite("ALERTAS_ACTIVAS_MAX")} alertas activas, que es el máximo. '
                'Marca como encontradas las que ya no necesites (Mi cuenta → Mis publicaciones).')
    return None


def bloqueo_adopciones(usuario):
    hace_un_dia = timezone.now() - timedelta(days=1)
    if usuario.mascotas_adopcion.filter(fecha_publicacion__gte=hace_un_dia).count() >= limite('ADOPCIONES_POR_DIA'):
        return f'Llegaste al máximo de {limite("ADOPCIONES_POR_DIA")} publicaciones de adopción por día.'
    return None


def bloqueo_mensajes(usuario):
    """2.1: no más de N mensajes por minuto.
    Usa un contador atómico (aguanta muchos envíos al mismo tiempo) y además revisa la base de datos."""
    import time
    from django.core.cache import cache
    from .models import Mensaje

    clave = f'mensajes:{usuario.id}:{int(time.time() // 60)}'
    cache.add(clave, 0, 120)
    try:
        if cache.incr(clave) > limite('MENSAJES_POR_MINUTO'):
            return 'Estás enviando mensajes muy rápido. Espera un minuto antes de seguir.'
    except ValueError:
        pass

    hace_un_minuto = timezone.now() - timedelta(minutes=1)
    if Mensaje.objects.filter(autor=usuario, fecha__gte=hace_un_minuto).count() >= limite('MENSAJES_POR_MINUTO'):
        return 'Estás enviando mensajes muy rápido. Espera un minuto antes de seguir.'
    return None


def _igual(a, b):
    return ' '.join(normalizar(p) for p in (a or '').split()) == ' '.join(normalizar(p) for p in (b or '').split())


def alerta_duplicada(usuario, tipo, mascota_datos, excluir_id=None):
    """3.2: ¿ya tiene este usuario una alerta ACTIVA igual?
    Igual = mismo tipo y especie, y además mismo nombre (perdidas) o misma descripción."""
    from .models import ReportePerdida

    activas = (ReportePerdida.objects
               .filter(mascota__usuario=usuario, tipo=tipo, estado_busqueda='activa',
                       mascota__especie=mascota_datos.get('especie'))
               .select_related('mascota'))
    if excluir_id:
        activas = activas.exclude(mascota_id=excluir_id)
    for r in activas:
        mismo_nombre = tipo == 'perdida' and mascota_datos.get('nombre') and _igual(r.mascota.nombre, mascota_datos['nombre'])
        misma_desc = _igual(r.mascota.descripcion, mascota_datos.get('descripcion'))
        if mismo_nombre or misma_desc:
            return r
    return None
