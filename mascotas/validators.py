"""
validators.py — Validaciones reutilizables (plan de pruebas)
------------------------------------------------------------
  validar_nombre_persona()  → casos 1.1 (ofensivo) y 1.2 (caracteres inválidos)
  validar_correo_real()     → caso 1.5 (correo inexistente)
  procesar_foto()           → caso 2.4 (fotos indebidas / archivos falsos)
  validar_ubicacion_chile() → caso 3.3 (ubicación inexistente o inválida)
"""
import re
import threading
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile

from .moderacion import contiene_ofensivas

# ---------------------------------------------------------------------
# 1.1 y 1.2  Nombre de la persona
# ---------------------------------------------------------------------
# Solo letras (con tildes y ñ), espacios, apóstrofe, guion y punto.  Nada de números, <, >, @, emojis…
REGEX_NOMBRE = re.compile(r"^[^\W\d_]+(?:[ '\-.][^\W\d_]+)*\.?$", re.UNICODE)


def limpiar_espacios(texto):
    return re.sub(r'\s+', ' ', texto or '').strip()


def validar_nombre_persona(nombre):
    nombre = limpiar_espacios(nombre)
    if len(nombre) < 2:
        raise ValidationError('El nombre es muy corto.')
    if len(nombre) > 60:
        raise ValidationError('El nombre es muy largo (máximo 60 caracteres).')
    if contiene_ofensivas(nombre):
        raise ValidationError('Ese nombre no está permitido. Por favor usa otro nombre.')
    if not REGEX_NOMBRE.match(nombre):
        raise ValidationError(
            'El nombre solo puede tener letras, espacios, guiones o apóstrofes. '
            'Elimina los números y caracteres especiales.')
    return nombre


# ---------------------------------------------------------------------
# 1.5  Correo inexistente
# ---------------------------------------------------------------------
# Errores típicos al escribir dominios conocidos
DOMINIOS_MAL_ESCRITOS = {
    'gmial.com': 'gmail.com', 'gmal.com': 'gmail.com', 'gmai.com': 'gmail.com', 'gamil.com': 'gmail.com',
    'gnail.com': 'gmail.com', 'gmail.co': 'gmail.com', 'gmail.cl': 'gmail.com', 'gmail.con': 'gmail.com',
    'gmail.cm': 'gmail.com', 'gmaill.com': 'gmail.com', 'hotmial.com': 'hotmail.com',
    'hotmal.com': 'hotmail.com', 'hotmai.com': 'hotmail.com', 'hotmail.co': 'hotmail.com',
    'hotmail.con': 'hotmail.com', 'hotmil.com': 'hotmail.com', 'outlok.com': 'outlook.com',
    'outlook.co': 'outlook.com', 'outloo.com': 'outlook.com', 'yahooo.com': 'yahoo.com',
    'yaho.com': 'yahoo.com', 'yahoo.co': 'yahoo.com', 'icloud.co': 'icloud.com',
    'usm.com': 'usm.cl', 'sansano.usm.com': 'sansano.usm.cl',
}
# Dominios reservados que nunca reciben correo, y correos temporales/desechables
DOMINIOS_FALSOS = {
    'example.com', 'example.org', 'example.net', 'test.com', 'test.cl', 'prueba.com', 'prueba.cl',
    'correo.com', 'email.com', 'asd.com', 'asdf.com', 'qwerty.com', 'aaa.com', 'abc.com', 'xxx.com',
    'mailinator.com', 'yopmail.com', 'guerrillamail.com', '10minutemail.com', 'tempmail.com',
    'temp-mail.org', 'trashmail.com', 'sharklasers.com', 'getnada.com', 'dispostable.com',
    'maildrop.cc', 'throwawaymail.com', 'fakeinbox.com',
}
TLD_RESERVADOS = {'test', 'example', 'invalid', 'localhost', 'local'}

_cache_dominios = {}


def _dominio_recibe_correo(dominio):
    """Pregunta al DNS si el dominio existe y puede recibir correo (registro MX o A).
    Devuelve True/False, o None si no se pudo averiguar (sin internet) → en ese caso no bloqueamos."""
    if dominio in _cache_dominios:
        return _cache_dominios[dominio]
    try:
        import dns.resolver  # librería dnspython
    except ImportError:
        return None

    resultado = {'valor': None}

    def consultar():
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 3
        try:
            resolver.resolve(dominio, 'MX')
            resultado['valor'] = True
        except dns.resolver.NXDOMAIN:
            resultado['valor'] = False  # el dominio no existe
        except dns.resolver.NoAnswer:
            try:  # sin MX: según el estándar se puede usar el registro A
                resolver.resolve(dominio, 'A')
                resultado['valor'] = True
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                resultado['valor'] = False
            except Exception:
                resultado['valor'] = None
        except Exception:
            resultado['valor'] = None  # sin internet, DNS caído, etc.

    hilo = threading.Thread(target=consultar, daemon=True)
    hilo.start()
    hilo.join(4)
    if resultado['valor'] is not None:
        _cache_dominios[dominio] = resultado['valor']
    return resultado['valor']


def validar_correo_real(email):
    email = (email or '').strip().lower()
    if '@' not in email:
        raise ValidationError('Ingresa un correo válido.')
    usuario, dominio = email.rsplit('@', 1)
    if dominio in DOMINIOS_MAL_ESCRITOS:
        raise ValidationError(f'¿Quisiste decir {usuario}@{DOMINIOS_MAL_ESCRITOS[dominio]}? Revisa tu correo.')
    if dominio in DOMINIOS_FALSOS or dominio.rsplit('.', 1)[-1] in TLD_RESERVADOS:
        raise ValidationError('Ese correo no es válido. Usa un correo real que revises.')
    if getattr(settings, 'VERIFICAR_DOMINIO_CORREO', True) and _dominio_recibe_correo(dominio) is False:
        raise ValidationError(f'El dominio "{dominio}" no existe o no recibe correos. Revisa que esté bien escrito.')
    return email


# ---------------------------------------------------------------------
# 2.4  Fotos: solo imágenes reales, de tamaño razonable, sin metadatos
# ---------------------------------------------------------------------
FORMATOS_PERMITIDOS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
MAX_MB = 5
MAX_PIXELES_LADO = 8000
LADO_FINAL = 1600


def procesar_foto(archivo):
    """Valida la foto y la vuelve a guardar como JPEG limpio.
    - Rechaza archivos que no son imágenes (aunque se llamen .jpg), muy pesados o gigantes.
    - Elimina los metadatos EXIF (que pueden incluir la ubicación GPS exacta de tu casa).
    - Reduce el tamaño para que la página cargue rápido."""
    if not archivo:
        return archivo
    from PIL import Image, ImageOps, UnidentifiedImageError

    if archivo.size > MAX_MB * 1024 * 1024:
        raise ValidationError(f'La foto pesa demasiado (máximo {MAX_MB} MB).')
    try:
        archivo.seek(0)
        with Image.open(archivo) as img:
            formato = img.format
            ancho, alto = img.size
            if formato not in FORMATOS_PERMITIDOS:
                raise ValidationError('Formato no permitido. Sube una foto JPG, PNG o WEBP.')
            if ancho > MAX_PIXELES_LADO or alto > MAX_PIXELES_LADO:
                raise ValidationError('La imagen es demasiado grande en resolución.')
            img.load()  # decodifica la imagen completa: si está corrupta, falla aquí
            img = ImageOps.exif_transpose(img)  # respeta la orientación del celular
            img = img.convert('RGB')
            img.thumbnail((LADO_FINAL, LADO_FINAL))
            salida = BytesIO()
            img.save(salida, format='JPEG', quality=85, optimize=True)  # sin EXIF
    except ValidationError:
        raise
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
        raise ValidationError('El archivo no es una imagen válida.')

    nombre = re.sub(r'[^\w-]', '', archivo.name.rsplit('.', 1)[0])[:40] or 'foto'
    salida.seek(0)
    return InMemoryUploadedFile(salida, 'foto', f'{nombre}.jpg', 'image/jpeg', salida.getbuffer().nbytes, None)


# ---------------------------------------------------------------------
# 3.3  Ubicación inexistente o inválida
# ---------------------------------------------------------------------
# Zonas (rectángulos lat/lng) donde aceptamos reportes: Chile continental e islas
ZONAS_CHILE = [
    (-56.6, -17.4, -76.0, -66.0),    # Chile continental (Arica a Cabo de Hornos)
    (-27.3, -27.0, -109.5, -109.2),  # Isla de Pascua
    (-33.9, -33.5, -80.9, -78.7),    # Archipiélago Juan Fernández
]


def validar_ubicacion_chile(lat, lng):
    if lat is None or lng is None:
        raise ValidationError('Marca en el mapa dónde se vio por última vez.')
    lat, lng = float(lat), float(lng)
    if lat != lat or lng != lng:  # NaN
        raise ValidationError('La ubicación no es válida. Marca un punto en el mapa.')
    if not any(a <= lat <= b and c <= lng <= d for a, b, c, d in ZONAS_CHILE):
        raise ValidationError('Esa ubicación está fuera de Chile. Marca un punto válido en el mapa.')
