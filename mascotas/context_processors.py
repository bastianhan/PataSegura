from django.db.models import Q

from .models import Mensaje


def chats_no_leidos(request):
    """Cantidad de mensajes sin leer, para el numerito de "Chats" en el menú."""
    if not request.user.is_authenticated:
        return {}
    usuario = request.user
    total = (Mensaje.objects
             .filter(leido=False)
             .filter(Q(conversacion__interesado=usuario) | Q(conversacion__reporte__mascota__usuario=usuario))
             .exclude(autor=usuario)
             .count())
    return {'chats_no_leidos': total}
