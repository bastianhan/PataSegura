"""
Pruebas automáticas de PataSegura.     Ejecutar con:   python manage.py test

La clase PlanDePruebas tiene UNA prueba por cada caso del plan de pruebas del grupo
(test_1_1 = caso 1.1, test_2_3 = caso 2.3, etc.). Si todas dicen "ok", ese caso está cubierto.
"""
import shutil
import re
import tempfile
from datetime import timedelta
from io import BytesIO
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .moderacion import censurar, contiene_ofensivas
from .models import Conversacion, Denuncia, Mascota, Mensaje, PerfilUsuario, ReportePerdida

MEDIA_PRUEBAS = tempfile.mkdtemp()

LIMITES_PRUEBA = {
    'ALERTAS_POR_DIA': 5, 'ALERTAS_ACTIVAS_MAX': 10, 'SEGUNDOS_ENTRE_ALERTAS': 0,
    'MENSAJES_POR_MINUTO': 10, 'ADOPCIONES_POR_DIA': 5, 'DENUNCIAS_PARA_OCULTAR': 3,
    'LARGO_MAX_MENSAJE': 1000, 'LARGO_MAX_DESCRIPCION': 1000, 'INTENTOS_LOGIN': 5,
    'MINUTOS_BLOQUEO_LOGIN': 15, 'MB_MAX_PETICION': 10,
}


def datos_registro(**cambios):
    datos = {'nombre_completo': 'Ana Pérez', 'email': 'ana@correo.cl', 'telefono': '',
             'password1': 'unaClaveSegura123', 'password2': 'unaClaveSegura123'}
    datos.update(cambios)
    return datos


def datos_alerta(**cambios):
    datos = {
        'tipo': 'perdida', 'nombre': 'Max', 'especie': 'perro',
        'descripcion': 'Golden con collar rojo y placa.', 'zona': 'Plaza Ñuñoa',
        'fecha_evento': timezone.localdate().isoformat(),
        'latitud': '-33.456000', 'longitud': '-70.598000',
    }
    datos.update(cambios)
    return datos


def imagen(formato='PNG', tam=(40, 40), exif=False):
    buf = BytesIO()
    img = Image.new('RGB', tam, (200, 120, 50))
    extra = {}
    if exif:
        datos_exif = Image.Exif()
        datos_exif[0x010F] = 'CamaraConGPS'
        extra['exif'] = datos_exif.tobytes()
    img.save(buf, format=formato, **extra)
    return buf.getvalue()


@override_settings(VERIFICAR_DOMINIO_CORREO=False, LIMITES=LIMITES_PRUEBA, MEDIA_ROOT=MEDIA_PRUEBAS)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_PRUEBAS, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.ana = User.objects.create_user('ana@correo.cl', 'ana@correo.cl', 'unaClaveSegura123', first_name='Ana')
        self.beto = User.objects.create_user('beto@correo.cl', 'beto@correo.cl', 'unaClaveSegura123', first_name='Beto')

    def publicar(self, usuario=None, **cambios):
        """Abre el formulario (para obtener el código de un solo uso) y lo envía."""
        self.client.force_login(usuario or self.ana)
        token = self.client.get(reverse('reportar_mascota')).context['token']
        return self.client.post(reverse('reportar_mascota'), datos_alerta(token=token, **cambios))

    def crear_reporte(self, usuario=None, nombre='Luna', **extra):
        m = Mascota.objects.create(usuario=usuario or self.ana, nombre=nombre, especie='gato',
                                   descripcion=f'Gata gris llamada {nombre}', zona='Providencia')
        return ReportePerdida.objects.create(mascota=m, latitud=-33.42, longitud=-70.61, **extra)


# =====================================================================
#  PLAN DE PRUEBAS — un test por cada caso
# =====================================================================
@override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
class ContrasenasTests(Base):
    def test_recuperacion_con_enlace_de_un_solo_uso(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': self.ana.email})
        self.assertRedirects(respuesta, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        enlace = re.search(r'http://testserver(/recuperar-contrasena/\S+)', mail.outbox[0].body).group(1)
        respuesta = self.client.get(enlace)
        self.assertEqual(respuesta.status_code, 302)
        ruta_formulario = respuesta['Location']
        self.assertContains(self.client.get(ruta_formulario), 'Crear contraseña nueva')
        respuesta = self.client.post(ruta_formulario, {'new_password1': 'SeguraNueva!481', 'new_password2': 'SeguraNueva!481'})
        self.assertRedirects(respuesta, reverse('password_reset_complete'))
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password('SeguraNueva!481'))
        respuesta = self.client.get(enlace, follow=True)
        self.assertContains(respuesta, 'Enlace no válido')

    def test_correo_desconocido_no_revela_existencia_de_cuenta(self):
        respuesta = self.client.post(reverse('password_reset'), {'email': 'nadie@correo.cl'})
        self.assertRedirects(respuesta, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_cambio_exige_sesion_y_contrasena_actual(self):
        ruta = reverse('password_change')
        self.assertEqual(self.client.get(ruta).status_code, 302)
        self.client.force_login(self.ana)
        datos = {'old_password': 'incorrecta', 'new_password1': 'SeguraNueva!481', 'new_password2': 'SeguraNueva!481'}
        self.assertEqual(self.client.post(ruta, datos).status_code, 200)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password('unaClaveSegura123'))
        datos['old_password'] = 'unaClaveSegura123'
        self.assertRedirects(self.client.post(ruta, datos), reverse('password_change_done'))
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password('SeguraNueva!481'))
        self.assertEqual(self.client.get(reverse('password_change_done')).status_code, 200)


class OrdenForoTests(Base):
    def test_orden_fecha_perdida_desempate_y_paginacion(self):
        fecha = timezone.now() - timedelta(days=1)
        reportes = [self.crear_reporte(nombre=f'Mascota {i}') for i in range(12)]
        for i, reporte in enumerate(reportes):
            ReportePerdida.objects.filter(pk=reporte.pk).update(
                fecha_publicacion=fecha + timedelta(days=i // 2),
                fecha_evento=timezone.localdate() - timedelta(days=i // 2),
            )
        primera = self.client.get(reverse('lista_mascotas_perdidas'))
        segunda = self.client.get(reverse('lista_mascotas_perdidas'), {'pagina': 2})
        esperados = [reportes[i].pk for i in (1, 0, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10)]
        self.assertEqual([r.pk for r in primera.context['reportes']], esperados[:10])
        self.assertEqual([r.pk for r in segunda.context['reportes']], esperados[10:])
        self.assertContains(primera, 'Publicado el')


class RegresionChat(Base):
    def test_api_ordenada_por_id_aunque_fecha_sea_distinta(self):
        reporte = self.crear_reporte()
        conv = Conversacion.objects.create(reporte=reporte, interesado=self.beto)
        primero = Mensaje.objects.create(conversacion=conv, autor=self.ana, texto='Primero')
        segundo = Mensaje.objects.create(conversacion=conv, autor=self.beto, texto='Segundo')
        Mensaje.objects.filter(pk=primero.pk).update(fecha=timezone.now() + timedelta(minutes=1))
        self.client.force_login(self.beto)
        respuesta = self.client.get(reverse('api_mensajes', args=[conv.pk]), {'desde': 0})
        self.assertEqual([m['id'] for m in respuesta.json()['mensajes']], [primero.pk, segundo.pk])


class RegresionMigracion(TransactionTestCase):
    def test_recupera_fechas_de_base_ya_migrada(self):
        executor = MigrationExecutor(connection)
        executor.migrate([('mascotas', '0004_denuncias_y_fotos_ocultas')])
        apps = executor.loader.project_state([('mascotas', '0004_denuncias_y_fotos_ocultas')]).apps
        Usuario = apps.get_model('auth', 'User')
        MascotaAnterior = apps.get_model('mascotas', 'Mascota')
        ReporteAnterior = apps.get_model('mascotas', 'ReportePerdida')
        usuario = Usuario.objects.create(username='migracion')
        fechas = [timezone.now() - timedelta(days=30), timezone.now() - timedelta(days=2)]
        ids = []
        for fecha in fechas:
            mascota = MascotaAnterior.objects.create(usuario_id=usuario.pk, nombre='Luna', especie='gato', descripcion='Gata', zona='Santiago')
            MascotaAnterior.objects.filter(pk=mascota.pk).update(fecha_publicacion=fecha)
            ids.append(ReporteAnterior.objects.create(mascota_id=mascota.pk, fecha_evento=timezone.localdate()).pk)
        executor = MigrationExecutor(connection)
        executor.migrate([('mascotas', '0005_restaurar_fechas_reportes')])
        reportes = ReportePerdida.objects.filter(pk__in=ids)
        self.assertEqual(list(reportes.order_by('-fecha_publicacion').values_list('pk', flat=True)), ids[::-1])
        self.assertEqual(list(reportes.order_by('pk').values_list('fecha_publicacion', flat=True)), fechas)


class PlanDePruebas(Base):

    # ---------------- Funcionalidad 1: Registrar al usuario ----------------
    def test_1_1_nombre_ofensivo_pide_otro_nombre(self):
        for nombre in ['Juan Weón', 'w3on culiao', 'P.u.t.a', 'Idiota Pérez']:
            r = self.client.post(reverse('registro'), datos_registro(nombre_completo=nombre, email='x@correo.cl'))
            self.assertContains(r, 'Ese nombre no está permitido', msg_prefix=nombre)
        self.assertFalse(User.objects.filter(email='x@correo.cl').exists())

    def test_1_2_caracteres_especiales_en_el_nombre(self):
        for nombre in ['Ana123', '<script>alert(1)</script>', 'Ana_Pérez', '😀😀', 'Ana@@']:
            r = self.client.post(reverse('registro'), datos_registro(nombre_completo=nombre, email='y@correo.cl'))
            self.assertContains(r, 'Elimina los números y caracteres especiales', msg_prefix=nombre)
        # Los nombres reales con tildes, ñ, guion o apóstrofe sí se aceptan
        r = self.client.post(reverse('registro'), datos_registro(nombre_completo="María-José O'Higgins Núñez", email='mj@correo.cl'))
        self.assertRedirects(r, reverse('mapa'))

    def test_1_3_casillas_en_blanco(self):
        r = self.client.post(reverse('registro'), {k: '' for k in datos_registro()})
        for texto in ['Escribe tu nombre completo.', 'Escribe tu correo electrónico.', 'Escribe una contraseña.']:
            self.assertContains(r, texto)
        # Solo espacios también cuenta como vacío
        r = self.client.post(reverse('registro'), datos_registro(nombre_completo='     ', email='z@correo.cl'))
        self.assertContains(r, 'Escribe tu nombre completo.')
        self.assertEqual(User.objects.count(), 2)

    def test_1_4_contrasenas_distintas(self):
        r = self.client.post(reverse('registro'), datos_registro(email='w@correo.cl', password2='otraClave999'))
        self.assertContains(r, 'Las contraseñas no coinciden')
        self.assertFalse(User.objects.filter(email='w@correo.cl').exists())

    def test_1_5_correo_inexistente(self):
        casos = {
            'ana@gmial.com': '¿Quisiste decir ana@gmail.com?',
            'ana@mailinator.com': 'Ese correo no es válido',
            'ana@example.com': 'Ese correo no es válido',
            'esto-no-es-correo': 'correo electrónico válido',
            'ana@@correo.cl': 'correo electrónico válido',
        }
        for correo, mensaje in casos.items():
            r = self.client.post(reverse('registro'), datos_registro(email=correo))
            self.assertContains(r, mensaje, msg_prefix=correo)
        # Dominio que no existe en internet (se simula la respuesta del DNS)
        with override_settings(VERIFICAR_DOMINIO_CORREO=True), \
                mock.patch('mascotas.validators._dominio_recibe_correo', return_value=False):
            r = self.client.post(reverse('registro'), datos_registro(email='ana@dominioquenoexiste123.cl'))
            self.assertContains(r, 'no existe o no recibe correos')
        # Sin internet no se bloquea a nadie
        with override_settings(VERIFICAR_DOMINIO_CORREO=True), \
                mock.patch('mascotas.validators._dominio_recibe_correo', return_value=None):
            r = self.client.post(reverse('registro'), datos_registro(email='nuevo@usm.cl'))
            self.assertRedirects(r, reverse('mapa'))

    # ---------------- Funcionalidad 2: Foro ----------------
    def test_2_1_spam_de_alertas_y_mensajes(self):
        # Alertas: después de publicar, hay que esperar antes de la siguiente
        limites = {**LIMITES_PRUEBA, 'SEGUNDOS_ENTRE_ALERTAS': 60}
        with override_settings(LIMITES=limites):
            self.publicar(nombre='Uno')
            r = self.publicar(nombre='Dos', descripcion='Otra descripción distinta')
            self.assertContains(r, 'Espera')
            self.assertEqual(Mascota.objects.count(), 1)
        # Mensajes: máximo 10 por minuto
        rep = self.crear_reporte(self.beto)
        conv = Conversacion.objects.create(reporte=rep, interesado=self.ana)
        self.client.force_login(self.ana)
        url = reverse('chat_detalle', args=[conv.id])
        for i in range(15):
            r = self.client.post(url, {'texto': f'spam {i}'}, HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(r.status_code, 429)
        self.assertIn('muy rápido', r.json()['error'])
        self.assertEqual(Mensaje.objects.count(), 10)

    def test_2_2_insultos_se_censuran(self):
        self.publicar(descripcion='Se escapó por culpa del weón del vecino, qué mierda')
        desc = Mascota.objects.get().descripcion
        self.assertNotIn('weón', desc)
        self.assertNotIn('mierda', desc)
        self.assertIn('w***', desc)
        # En el chat también
        rep = self.crear_reporte(self.beto)
        conv = Conversacion.objects.create(reporte=rep, interesado=self.ana)
        r = self.client.post(reverse('chat_detalle', args=[conv.id]), {'texto': 'eres un ctm'},
                             HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(r.json()['mensaje']['texto'], 'eres un c**')
        self.assertTrue(r.json()['aviso'])
        # Sin falsos positivos con palabras normales
        self.assertFalse(contiene_ofensivas('Mi perra se perdió en la computadora del Disputado'))
        self.assertEqual(censurar('W3OOON'), 'W*****')

    def test_2_3_mensaje_o_alerta_en_blanco(self):
        rep = self.crear_reporte(self.beto)
        conv = Conversacion.objects.create(reporte=rep, interesado=self.ana)
        self.client.force_login(self.ana)
        for texto in ['', '    ', '\n\n']:
            r = self.client.post(reverse('chat_detalle', args=[conv.id]), {'texto': texto},
                                 HTTP_X_REQUESTED_WITH='fetch')
            self.assertEqual(r.status_code, 400)
            self.assertIn('en blanco', r.json()['error'])
        self.assertEqual(Mensaje.objects.count(), 0)
        r = self.publicar(nombre=' ', descripcion='   ', zona='  ')
        self.assertContains(r, 'Faltan datos obligatorios')
        self.assertEqual(Mascota.objects.count(), 1)  # solo la del crear_reporte

    def test_2_4_fotos_indebidas_o_falsas(self):
        # a) Un archivo que no es imagen, aunque se llame .jpg
        falso = SimpleUploadedFile('virus.jpg', b'MZ\x90\x00 esto no es una imagen', content_type='image/jpeg')
        r = self.publicar(foto=falso)
        self.assertContains(r, 'imagen válida')
        # b) Una imagen gigante en resolución (posible ataque para colgar el servidor)
        enorme = SimpleUploadedFile('enorme.png', imagen('PNG', (9000, 300)), content_type='image/png')
        r = self.publicar(nombre='Grande', foto=enorme)
        self.assertContains(r, 'demasiado grande')
        # c) Una foto real se guarda limpia: JPEG, sin metadatos (EXIF con ubicación)
        buena = SimpleUploadedFile('max.png', imagen('JPEG', exif=True), content_type='image/jpeg')
        self.publicar(nombre='ConFoto', foto=buena)
        m = Mascota.objects.get(nombre='ConFoto')
        with Image.open(m.foto.path) as img:
            self.assertEqual(img.format, 'JPEG')
            self.assertEqual(len(img.getexif()), 0)
        # d) Con 3 denuncias de personas distintas, la foto se oculta sola
        for i in range(3):
            u = User.objects.create_user(f'd{i}@correo.cl', f'd{i}@correo.cl', 'x')
            self.client.force_login(u)
            self.client.post(reverse('denunciar', args=[m.id]), {'motivo': 'foto'})
        m.refresh_from_db()
        self.assertTrue(m.foto_oculta)
        self.assertIsNone(self.client.get(reverse('api_reportes')).json()['reportes'][0]['foto'])
        # Una persona no puede denunciar dos veces
        self.client.post(reverse('denunciar', args=[m.id]), {'motivo': 'foto'})
        self.assertEqual(Denuncia.objects.count(), 3)

    def test_2_5_mensaje_muy_largo(self):
        rep = self.crear_reporte(self.beto)
        conv = Conversacion.objects.create(reporte=rep, interesado=self.ana)
        self.client.force_login(self.ana)
        r = self.client.post(reverse('chat_detalle', args=[conv.id]), {'texto': 'a' * 5000},
                             HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(r.status_code, 400)
        self.assertIn('límite es 1000', r.json()['error'])
        r = self.publicar(descripcion='b' * 1500)
        self.assertContains(r, 'el límite es 1000')
        self.assertEqual(Mensaje.objects.count(), 0)

    # ---------------- Funcionalidad 3: Mapa ----------------
    def test_3_1_limite_de_alertas_por_usuario(self):
        for i in range(5):
            self.publicar(nombre=f'Perro{i}', descripcion=f'Descripción número {i} del perro')
        self.assertEqual(Mascota.objects.count(), 5)
        r = self.publicar(nombre='Sexto', descripcion='Este ya no debería publicarse')
        self.assertContains(r, 'máximo de 5 alertas por día')
        self.assertEqual(Mascota.objects.count(), 5)
        # Máximo de alertas activas a la vez
        ReportePerdida.objects.update(fecha_publicacion=timezone.now() - timedelta(days=2))
        for i in range(5):
            self.crear_reporte(self.ana, nombre=f'Extra{i}')
        ReportePerdida.objects.update(fecha_publicacion=timezone.now() - timedelta(days=2))
        r = self.publicar(nombre='Once', descripcion='Excede las activas')
        self.assertContains(r, 'alertas activas')

    def test_3_2_alertas_iguales(self):
        self.publicar()
        r = self.publicar()  # exactamente la misma
        self.assertContains(r, 'Ya tienes una alerta activa igual')
        r = self.publicar(nombre='  MAX ', descripcion='Otra descripción')  # mismo nombre con otras mayúsculas
        self.assertContains(r, 'Ya tienes una alerta activa igual')
        self.assertEqual(Mascota.objects.count(), 1)
        # Otra persona sí puede publicar una alerta parecida
        self.publicar(usuario=self.beto)
        self.assertEqual(Mascota.objects.count(), 2)

    def test_3_3_ubicacion_invalida(self):
        casos = [
            ('', ''), ('abc', 'xyz'), ('NaN', 'NaN'), ('1e309', '5'), ('-91', '0'), ('0', '200'),
            ('48.8566', '2.3522'),     # París: fuera de Chile
            ('-33.45', '-60.0'),       # Argentina
            ('-33.456', ''),           # falta la longitud
        ]
        for lat, lng in casos:
            r = self.publicar(latitud=lat, longitud=lng)
            self.assertEqual(r.status_code, 200, f'{lat},{lng}')
            self.assertTrue('ubicación' in r.content.decode().lower() or 'Marca en el mapa' in r.content.decode(),
                            f'{lat},{lng}')
        self.assertEqual(Mascota.objects.count(), 0)
        # Isla de Pascua sí es válida
        self.publicar(latitud='-27.1127', longitud='-109.3497')
        self.assertEqual(Mascota.objects.count(), 1)

    def test_3_4_apretar_publicar_muchas_veces(self):
        self.client.force_login(self.ana)
        token = self.client.get(reverse('reportar_mascota')).context['token']
        for _ in range(5):  # el mismo formulario enviado 5 veces seguidas
            self.client.post(reverse('reportar_mascota'), datos_alerta(token=token))
        self.assertEqual(Mascota.objects.count(), 1)
        # Sin código (alguien enviando el formulario con un programa) tampoco se publica
        self.client.post(reverse('reportar_mascota'), datos_alerta(nombre='Bot'))
        self.assertEqual(Mascota.objects.count(), 1)

    def test_3_5_manipular_reporte_de_otro_usuario(self):
        rep = self.crear_reporte(self.beto)
        mid = rep.mascota_id
        self.client.force_login(self.ana)
        # Cambiar el estado, editar (ubicación) o leer su chat → "No tienes acceso"
        r = self.client.post(reverse('cambiar_estado', args=[mid]), {'estado_busqueda': 'cerrada'})
        self.assertContains(r, 'No tienes acceso', status_code=403)
        r = self.client.get(reverse('editar_reporte', args=[mid]))
        self.assertContains(r, 'No tienes acceso', status_code=403)
        r = self.client.post(reverse('editar_reporte', args=[mid]),
                             datos_alerta(latitud='-20.0', longitud='-70.0', nombre='Hackeado'))
        self.assertEqual(r.status_code, 403)
        rep.refresh_from_db()
        self.assertEqual(rep.estado_busqueda, 'activa')
        self.assertEqual(float(rep.latitud), -33.42)
        self.assertEqual(rep.mascota.nombre, 'Luna')
        # Intentar publicar a nombre de otro usuario enviando su id
        self.publicar(usuario=self.ana, usuario_id=self.beto.id, nombre='Suplantado')
        self.assertEqual(Mascota.objects.get(nombre='Suplantado').usuario, self.ana)
        # El dueño sí puede editar su ubicación
        self.client.force_login(self.beto)
        self.client.post(reverse('editar_reporte', args=[mid]),
                         datos_alerta(nombre='Luna', especie='gato', latitud='-33.40', longitud='-70.60'))
        rep.refresh_from_db()
        self.assertEqual(float(rep.latitud), -33.40)


# =====================================================================
#  "Que no se caiga": entradas raras, ataques y seguridad general
# =====================================================================
class RobustezTests(Base):
    def test_ninguna_pagina_da_error_500_con_parametros_raros(self):
        rep = self.crear_reporte(self.beto)
        conv = Conversacion.objects.create(reporte=rep, interesado=self.ana)
        self.client.force_login(self.ana)
        urls = [
            '/perdidas/?pagina=abc', '/perdidas/?pagina=-5', '/perdidas/?pagina=999999',
            '/perdidas/?especie=<script>', '/hallazgos/?especie=dragon', '/mapa/?ver=xyz',
            f'/chats/{conv.id}/mensajes/?desde=abc', f'/chats/{conv.id}/mensajes/?desde=99999999999999999999',
            '/perdidas/999999/', '/chats/999999/', '/perdidas/reportar/?tipo=<b>',
        ]
        for url in urls:
            self.assertIn(self.client.get(url).status_code, (200, 404), url)

    def test_formulario_con_datos_basura_no_se_cae(self):
        basura = datos_alerta(especie='dragon', fecha_evento='2026-13-45', latitud='💥', nombre='x' * 5000,
                              descripcion='\x00\x01' * 10, telefono_contacto='llámame')
        r = self.publicar(**basura)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Mascota.objects.count(), 0)

    def test_html_malicioso_se_muestra_como_texto(self):
        self.publicar(nombre='<script>alert(1)</script>', descripcion='<img src=x onerror=alert(1)> perrito')
        html = self.client.get(reverse('lista_mascotas_perdidas')).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_peticion_gigante_se_rechaza(self):
        r = self.client.post(reverse('reportar_mascota'), data=b'x', content_type='text/plain',
                             CONTENT_LENGTH=str(50 * 1024 * 1024))
        self.assertEqual(r.status_code, 413)

    def test_bloqueo_tras_muchos_intentos_de_login(self):
        for _ in range(5):
            self.client.post(reverse('login'), {'username': 'ana@correo.cl', 'password': 'mala'})
        r = self.client.post(reverse('login'), {'username': 'ana@correo.cl', 'password': 'unaClaveSegura123'})
        self.assertContains(r, 'Demasiados intentos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_redireccion_externa_bloqueada(self):
        rep = self.crear_reporte(self.ana)
        self.client.force_login(self.ana)
        r = self.client.post(reverse('cambiar_estado', args=[rep.mascota_id]),
                             {'estado_busqueda': 'encontrada', 'volver': 'https://sitio-malo.com'})
        self.assertEqual(r['Location'], reverse('detalle_mascota', args=[rep.mascota_id]))

    def test_foro_con_miles_de_alertas_sigue_rapido(self):
        usuarios = [User(username=f'u{i}@c.cl', email=f'u{i}@c.cl') for i in range(50)]
        User.objects.bulk_create(usuarios)
        usuarios = list(User.objects.filter(username__endswith='@c.cl'))
        mascotas = Mascota.objects.bulk_create([
            Mascota(usuario=usuarios[i % 50], nombre=f'M{i}', especie='perro', descripcion='Perro de prueba', zona='Stgo')
            for i in range(2000)])
        ReportePerdida.objects.bulk_create([
            ReportePerdida(mascota=m, latitud=-33.4 - (i % 100) / 1000, longitud=-70.6) for i, m in enumerate(mascotas)])
        with self.assertNumQueries(2):  # siempre las mismas consultas, sin importar cuántas alertas haya
            r = self.client.get(reverse('lista_mascotas_perdidas'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['reportes']), 10)  # paginado
        self.assertEqual(len(self.client.get(reverse('api_reportes')).json()['reportes']), 2000)


# =====================================================================
#  Funcionamiento normal (que lo arreglado no rompa lo que ya andaba)
# =====================================================================
class FuncionamientoNormalTests(Base):
    def test_registro_y_login_correctos(self):
        r = self.client.post(reverse('registro'), datos_registro(email='nueva@correo.cl', telefono='+56 9 1234 5678'))
        self.assertRedirects(r, reverse('mapa'))
        u = User.objects.get(email='nueva@correo.cl')
        self.assertEqual(u.perfil.telefono, '+56 9 1234 5678')
        self.client.logout()
        r = self.client.post(reverse('login'), {'username': 'nueva@correo.cl', 'password': 'unaClaveSegura123'})
        self.assertEqual(r.status_code, 302)

    def test_alerta_completa_se_publica(self):
        r = self.publicar()
        m = Mascota.objects.get()
        self.assertRedirects(r, f"{reverse('lista_mascotas_perdidas')}?nueva={m.id}#m-{m.id}", fetch_redirect_response=False)
        self.assertEqual(m.reporte.coordenadas, {'lat': -33.456, 'lng': -70.598})
        self.assertContains(self.client.get(reverse('lista_mascotas_perdidas')), 'Max')

    def test_hallazgo_sin_nombre(self):
        self.publicar(tipo='hallazgo', nombre='')
        self.assertEqual(ReportePerdida.objects.get().tipo, 'hallazgo')

    def test_chat_normal(self):
        rep = self.crear_reporte(self.beto)
        self.client.force_login(self.ana)
        self.client.post(reverse('iniciar_chat', args=[rep.mascota_id]))
        conv = Conversacion.objects.get()
        self.client.post(reverse('chat_detalle', args=[conv.id]), {'texto': 'Lo vi en la plaza'})
        self.client.force_login(self.beto)
        self.assertEqual(self.client.get(reverse('lista_chats')).context['chats_no_leidos'], 1)
        self.client.get(reverse('chat_detalle', args=[conv.id]))
        self.assertTrue(Mensaje.objects.get().leido)

    def test_paginas_cargan(self):
        for nombre in ['login', 'registro', 'mapa', 'lista_mascotas_perdidas', 'lista_hallazgos',
                       'lista_adopciones', 'lista_establecimientos']:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
        PerfilUsuario.de(self.ana)
        self.client.force_login(self.ana)
        for nombre in ['mi_cuenta', 'mis_publicaciones', 'configuracion', 'lista_chats', 'reportar_mascota',
                       'publicar_adopcion']:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
