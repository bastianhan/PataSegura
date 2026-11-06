"""
Carga datos de ejemplo para probar y presentar el prototipo.

    python manage.py cargar_demo          → crea los datos (si no existen)
    python manage.py cargar_demo --reset  → borra los datos de ejemplo y los vuelve a crear

Cuenta de prueba:  demo@patasegura.cl  /  patasegura123
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from mascotas.models import (Adopcion, Conversacion, Establecimiento, Mascota, Mensaje,
                             PerfilUsuario, ReportePerdida)

CLAVE = 'patasegura123'
DOMINIO = '@patasegura.cl'

USUARIOS = [
    # (correo, nombre, apellido, teléfono, comuna)
    ('demo', 'Usuario', 'Demo', '+56 9 1111 1111', 'San Joaquín'),
    ('sofia', 'Sofía', 'Rojas', '+56 9 2222 2222', 'Providencia'),
    ('camilo', 'Camilo', 'Pérez', '+56 9 3333 3333', 'Providencia'),
    ('diego', 'Diego', 'Muñoz', '', 'Ñuñoa'),
    ('valentina', 'Valentina', 'Soto', '+56 9 5555 5555', 'Providencia'),
    ('andres', 'Andrés', 'Fuentes', '', 'Macul'),
    ('huellitas', 'Refugio', 'Huellitas', '+56 2 2345 6789', 'San Joaquín'),
]

# (tipo, dueño, nombre, especie, raza, color, descripción, lat, lng, días atrás, referencia)
REPORTES = [
    ('perdida', 'sofia', 'Max', 'perro', 'Golden Retriever', 'Dorado', 'Golden de pelo largo, collar rojo con placa. Muy amistoso, responde a su nombre.', -33.4262, -70.6155, 2, 'Plaza Las Lilas, Providencia'),
    ('perdida', 'camilo', 'Luna', 'gato', 'Mestizo', 'Gris atigrado', 'Gata atigrada gris con manchas blancas en el pecho. Es asustadiza.', -33.4291, -70.6098, 4, 'Pedro de Valdivia con Eliodoro Yáñez'),
    ('perdida', 'demo', 'Toby', 'perro', 'Jack Russell', 'Blanco y café', 'Blanco con manchas cafés en la cara, cola corta. Lleva arnés azul.', -33.4312, -70.6191, 6, 'Parque Inés de Suárez'),
    ('perdida', 'valentina', 'Nala', 'gato', 'Mestizo', 'Negro', 'Gata completamente negra, ojos amarillos, collar con cascabel.', -33.4248, -70.6122, 8, 'Calle Los Leones'),
    ('perdida', 'andres', 'Rocky', 'perro', 'Bulldog Francés', 'Atigrado', 'Bulldog francés atigrado, orejas grandes, ronca al respirar.', -33.4275, -70.6201, 1, 'Metro Pedro de Valdivia'),
    ('perdida', 'diego', 'Coco', 'perro', 'Poodle', 'Damasco', 'Poodle toy color damasco, recién peluqueado.', -33.4303, -70.6135, 3, 'Av. Providencia 2100'),
    ('perdida', 'sofia', 'Simba', 'gato', 'Mestizo', 'Naranjo', 'Gato naranjo grande, castrado, muy dócil.', -33.4555, -70.5981, 5, 'Plaza Ñuñoa'),
    ('perdida', 'camilo', 'Kira', 'perro', 'Pastor Alemán', 'Negro y café', 'Pastor alemán hembra, joven, collar negro.', -33.4580, -70.6020, 2, 'Estadio Nacional, acceso norte'),
    ('perdida', 'valentina', 'Mía', 'gato', 'Siamés', 'Crema', 'Siamesa de ojos azules, muy maullona.', -33.4532, -70.5952, 9, 'Irarrázaval 3400'),
    ('perdida', 'diego', 'Bruno', 'perro', 'Labrador', 'Chocolate', 'Labrador chocolate, cojea un poco de la pata trasera.', -33.4602, -70.5993, 7, 'Av. Grecia con Pedro de Valdivia'),
    ('perdida', 'andres', 'Canela', 'perro', 'Quiltro', 'Canela', 'Quiltra color canela, mediana, orejas caídas.', -33.4905, -70.6170, 1, 'Cerca del campus San Joaquín'),
    ('perdida', 'sofia', 'Michi', 'gato', 'Mestizo', 'Blanco y negro', 'Gato blanco con negro, tiene la punta de una oreja cortada (esterilizado).', -33.4930, -70.6202, 4, 'Av. Vicuña Mackenna 4860'),
    ('perdida', 'camilo', 'Thor', 'perro', 'Husky', 'Gris y blanco', 'Husky siberiano, un ojo azul y otro café.', -33.5110, -70.7570, 3, 'Plaza de Maipú'),
    ('perdida', 'valentina', 'Pelusa', 'gato', 'Persa', 'Blanco', 'Gata persa blanca, pelo largo, muy tranquila.', -33.4372, -70.6506, 10, 'Barrio Lastarria'),
    ('hallazgo', 'demo', '', 'perro', 'Quiltro', 'Negro', 'Encontré un perrito negro pequeño con collar verde sin placa. Está en mi casa a salvo.', -33.4410, -70.6400, 1, 'Parque Forestal'),
    ('hallazgo', 'diego', '', 'gato', '', 'Gris', 'Gatito gris de unos 3 meses maullando en un estacionamiento.', -33.4470, -70.6090, 2, 'Av. Matta'),
]

ESTABLECIMIENTOS = [
    ('Refugio Huellitas San Joaquín', 'refugio', 'Av. Departamental 1200, San Joaquín', '+56 2 2345 6789', 'Sáb y dom 11:00–17:00', 'Rescatamos perros y gatos de la calle desde 2015.'),
    ('Fundación Patitas Felices', 'refugio', 'Av. Irarrázaval 2800, Ñuñoa', '+56 9 8765 4321', 'Lun a vie 10:00–18:00', 'Hogar temporal para gatitos y perros senior.'),
    ('Clínica Veterinaria Los Aromos', 'veterinaria', 'Av. Vicuña Mackenna 3900, Macul', '+56 2 2222 3333', 'Urgencias 24 horas', 'Atención general, urgencias y lector de microchip gratuito.'),
    ('Tienda Mundo Mascota', 'tienda', 'Av. Providencia 1650, Providencia', '', 'Lun a sáb 10:00–20:00', 'Alimentos, accesorios y placas de identificación.'),
]

ADOPCIONES = [
    ('Chispa', 'perro', '2 años', 'Mediana, juguetona y buena con niños. Vacunas al día.', 'San Joaquín'),
    ('Oreo', 'gato', '6 meses', 'Gatito blanco y negro, muy curioso. Busca familia responsable.', 'San Joaquín'),
    ('Abuelo Tito', 'perro', '10 años', 'Perro senior tranquilo, ideal para departamento.', 'Ñuñoa'),
]


class Command(BaseCommand):
    help = 'Carga datos de ejemplo (usuarios, reportes con coordenadas, chats, refugios).'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Borra los datos de ejemplo antes de crearlos.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        correos = [u[0] + DOMINIO for u in USUARIOS]
        if opciones['reset']:
            User.objects.filter(username__in=correos).delete()  # borra también sus mascotas, chats, etc.
            Establecimiento.objects.filter(nombre__in=[e[0] for e in ESTABLECIMIENTOS]).delete()
        elif User.objects.filter(username='demo' + DOMINIO).exists():
            self.stdout.write(self.style.WARNING('Los datos de ejemplo ya existen. Usa --reset para recrearlos.'))
            return

        hoy = timezone.localdate()
        usuarios = {}
        for alias, nombre, apellido, telefono, comuna in USUARIOS:
            u = User.objects.create_user(alias + DOMINIO, alias + DOMINIO, CLAVE, first_name=nombre, last_name=apellido)
            PerfilUsuario.objects.create(usuario=u, telefono=telefono, comuna=comuna, mostrar_telefono=bool(telefono))
            usuarios[alias] = u

        reportes = {}
        for i, (tipo, dueno, nombre, especie, raza, color, desc, lat, lng, dias, ref) in enumerate(REPORTES):
            u = usuarios[dueno]
            m = Mascota.objects.create(
                usuario=u, nombre=nombre, especie=especie, raza=raza, color=color, descripcion=desc, zona=ref,
                telefono_contacto=u.perfil.telefono, mostrar_telefono=bool(u.perfil.telefono))
            r = ReportePerdida.objects.create(
                mascota=m, tipo=tipo, latitud=lat, longitud=lng, fecha_evento=hoy - timedelta(days=dias))
            # que el orden del foro coincida con la fecha del evento
            ReportePerdida.objects.filter(id=r.id).update(
                fecha_publicacion=timezone.now() - timedelta(days=dias, minutes=i))
            reportes[nombre or desc] = r

        for nombre, tipo, direccion, telefono, horario, desc in ESTABLECIMIENTOS:
            Establecimiento.objects.create(nombre=nombre, tipo=tipo, direccion=direccion,
                                           telefono=telefono, horario=horario, descripcion=desc)

        for nombre, especie, edad, desc, zona in ADOPCIONES:
            Adopcion.objects.create(usuario=usuarios['huellitas'], nombre=nombre, especie=especie,
                                    edad_aproximada=edad, descripcion=desc, zona=zona)

        demo = usuarios['demo']

        def chat(reporte, interesado, mensajes):
            conv = Conversacion.objects.create(reporte=reporte, interesado=interesado)
            otro = conv.dueno if interesado == demo else interesado
            for j, (de_demo, texto, minutos) in enumerate(mensajes):
                Mensaje.objects.create(conversacion=conv, autor=demo if de_demo else otro, texto=texto,
                                       leido=de_demo or j < len(mensajes) - 1)
            for j, m in enumerate(conv.mensajes.all()):
                Mensaje.objects.filter(id=m.id).update(fecha=timezone.now() - timedelta(minutes=mensajes[j][2]))
            Conversacion.objects.filter(id=conv.id).update(
                actualizada=timezone.now() - timedelta(minutes=mensajes[-1][2]))

        chat(reportes['Max'], demo, [
            (False, '¡Hola! ¿Viste a un perro parecido a este? Se me perdió aquí en la zona.', 32),
            (True, '¡Hola Sofía! Sí, lo vi hace un rato en el parque de la esquina. Tenía el mismo collar.', 28),
            (False, '¡Muchas gracias! ¿Podrías decirme más o menos a qué hora lo viste? Ya vamos para allá.', 24),
            (True, 'Claro, fue alrededor de las 14:10. Está cerca de la pileta.', 21),
            (False, '¡Muchas gracias por avisar! Voy en camino 🙏', 6),
        ])
        chat(reportes['Luna'], demo, [
            (True, 'Hola, creo que vi a Luna cerca del metro.', 300),
            (False, 'Sí, la vi cerca del metro ayer', 150),
        ])
        chat(reportes['Toby'], usuarios['diego'], [
            (False, 'Hola, ¿Toby tiene microchip?', 1600),
            (True, 'Sí, está registrado.', 1550),
            (False, 'Gracias por el dato! Vamos a ir a buscar a Toby.', 1500),
        ])
        chat(reportes['Nala'], demo, [
            (True, '¿Nala sigue perdida?', 3000),
            (False, 'Te dejé mi número para que me avises si la ves.', 2900),
        ])

        self.stdout.write(self.style.SUCCESS(
            f'✔ Datos de ejemplo creados: {len(USUARIOS)} usuarios, {len(REPORTES)} reportes, '
            f'{len(ESTABLECIMIENTOS)} establecimientos y {len(ADOPCIONES)} adopciones.\n'
            f'  Cuenta de prueba: demo{DOMINIO} / {CLAVE}'))
