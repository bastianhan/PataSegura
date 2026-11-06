from django.conf import settings
from django.http import HttpResponse


class LimiteTamanoPeticion:
    """Rechaza peticiones gigantes (por ejemplo, alguien subiendo un archivo de 2 GB)
    ANTES de que Django las procese, para que el servidor no se quede sin memoria ni disco."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        maximo = settings.LIMITES['MB_MAX_PETICION'] * 1024 * 1024
        try:
            largo = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            largo = 0
        if largo > maximo:
            return HttpResponse(
                f'<h1>Archivo demasiado grande</h1><p>El máximo es {settings.LIMITES["MB_MAX_PETICION"]} MB. '
                '<a href="javascript:history.back()">Volver</a></p>',
                status=413,
            )
        return self.get_response(request)
