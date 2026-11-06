"""Etiquetas propias para las plantillas.  Uso:  {% load patasegura %}

    {% icono 'mapa' %}            → ícono SVG
    {% huella 24 %}               → huella (logo)
    {{ reporte|hace_dias }}       → "Hace 3 días"
    {{ reporte|clase_urgencia }}  → clase CSS del color de la etiqueta
    {{ user|iniciales }}          → "BH"
"""
from django import template
from django.utils.html import format_html
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()

ICONOS = {
    'mapa': '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z"/><path d="M9 4v14M15 6v14"/>',
    'foro': '<path d="M4 5h16v11H8l-4 4V5Z"/><path d="M8 9h8M8 12h5"/>',
    'chat': '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z"/>',
    'publicar': '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M12 8v8M8 12h8"/>',
    'usuario': '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    'buscar': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    'ubicacion': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><circle cx="12" cy="12" r="7"/>',
    'pin': '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z"/><circle cx="12" cy="9.5" r="2.5"/>',
    'atras': '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    'derecha': '<path d="m9 6 6 6-6 6"/>',
    'enviar': '<path d="M4 12 20 4l-4 16-4-7-8-1Z"/>',
    'campana': '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4l2-2Z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    'ajustes': '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1"/>',
    'salir': '<path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10"/>',
    'correo': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    'candado': '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    'ojo': '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    'telefono': '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/>',
    'corazon': '<path d="M12 20s-7-4.4-9-9a5 5 0 0 1 9-3 5 5 0 0 1 9 3c-2 4.6-9 9-9 9Z"/>',
    'lupa': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6"/>',
    'reloj': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'check': '<path d="m5 12 5 5 9-10"/>',
    'clip': '<path d="m21 11-8.5 8.5a5 5 0 0 1-7-7L14 4a3.5 3.5 0 0 1 5 5l-8.5 8.5a2 2 0 0 1-3-3L15 7"/>',
    'casa': '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>',
    'camara': '<path d="M4 8h3l2-3h6l2 3h3v11H4V8Z"/><circle cx="12" cy="13" r="3.5"/>',
    'tienda': '<path d="M4 9h16l-1-5H5L4 9Z"/><path d="M5 9v11h14V9M9 20v-6h6v6"/>',
    'cruz': '<path d="M12 5v14M5 12h14"/>',
    'lista': '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
}

HUELLA = (
    '<ellipse cx="6" cy="9.5" rx="2.1" ry="2.7" transform="rotate(-18 6 9.5)"/>'
    '<ellipse cx="10" cy="5.6" rx="2.1" ry="2.8"/>'
    '<ellipse cx="14.6" cy="5.6" rx="2.1" ry="2.8"/>'
    '<ellipse cx="18.4" cy="9.6" rx="2.1" ry="2.7" transform="rotate(18 18.4 9.6)"/>'
    '<path d="M12.3 11.2c2.6 0 5.6 3.6 5.6 6.1 0 1.8-1.4 2.6-2.9 2.6-1.2 0-1.8-.6-2.7-.6s-1.6.6-2.8.6'
    'c-1.5 0-2.9-.8-2.9-2.6 0-2.5 3.1-6.1 5.7-6.1Z"/>'
)


@register.simple_tag
def icono(nombre, tam=20):
    return format_html(
        '<svg class="icono" width="{0}" height="{0}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{1}</svg>',
        tam, mark_safe(ICONOS.get(nombre, '')),
    )


@register.simple_tag
def huella(tam=24, color='currentColor'):
    return format_html(
        '<svg class="huella" width="{0}" height="{0}" viewBox="0 0 24 24" fill="{1}" aria-hidden="true">{2}</svg>',
        tam, color, mark_safe(HUELLA),
    )


@register.filter
def hace_dias(reporte):
    dias = reporte.dias_desde_evento
    if dias == 0:
        return 'Hoy'
    return 'Hace 1 día' if dias == 1 else f'Hace {dias} días'


@register.filter
def clase_urgencia(reporte):
    """Más reciente = más urgente (rojo); con los días pasa a ámbar y verde."""
    dias = reporte.dias_desde_evento
    if dias <= 2:
        return 'badge-rojo'
    return 'badge-ambar' if dias <= 5 else 'badge-verde'


@register.filter
def iniciales(usuario):
    nombre = usuario.get_full_name() or usuario.username
    partes = [p for p in nombre.replace('@', ' ').split() if p]
    return ''.join(p[0].upper() for p in partes[:2]) or '?'


@register.filter
def nombre_visible(usuario):
    return usuario.get_full_name() or usuario.username.split('@')[0]


EMOJI = {'perro': '🐶', 'gato': '🐱'}


@register.filter
def emoji_especie(especie):
    return EMOJI.get(especie, '🐾')


MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']


@register.filter
def hora_chat(fecha):
    """Hoy → '14:20' · ayer → 'Ayer' · antes → '3 nov'."""
    local = timezone.localtime(fecha)
    dias = (timezone.localdate() - local.date()).days
    if dias == 0:
        return local.strftime('%H:%M')
    if dias == 1:
        return 'Ayer'
    return f'{local.day} {MESES_CORTOS[local.month - 1]}'
