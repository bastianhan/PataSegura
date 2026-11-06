from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

ESPECIES = [
    ('perro', 'Perro'),
    ('gato', 'Gato'),
    ('otro', 'Otro'),
]


# =====================================================================
#  USUARIO
# ---------------------------------------------------------------------
#  La entidad USUARIO se arma con dos partes:
#   - datos_cuenta   → el modelo User que trae Django (correo, contraseña
#                      encriptada, fecha de registro). Lo usa el login.
#   - datos_contacto → este modelo PerfilUsuario (teléfono, comuna…),
#                      unido 1 a 1 con el User.
#  Se accede así:  request.user.perfil.datos_contacto
# =====================================================================
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=30, blank=True)
    comuna = models.CharField(max_length=80, blank=True)
    mostrar_telefono = models.BooleanField(
        default=False, help_text='Si está marcado, tu teléfono aparece en tus publicaciones.'
    )

    @property
    def datos_contacto(self):
        return {
            'nombre': self.usuario.get_full_name() or self.usuario.username,
            'correo': self.usuario.email,
            'telefono': self.telefono if self.mostrar_telefono else '',
            'comuna': self.comuna,
        }

    @property
    def datos_cuenta(self):
        u = self.usuario
        return {
            'usuario': u.username,
            'email': u.email,
            'fecha_registro': u.date_joined,
            'activo': u.is_active,
        }

    def __str__(self):
        return f'Perfil de {self.usuario.username}'

    @classmethod
    def de(cls, usuario):
        """Devuelve el perfil del usuario (y lo crea si todavía no existe)."""
        perfil, _ = cls.objects.get_or_create(usuario=usuario)
        return perfil


# =====================================================================
#  MASCOTA  (nombre, descripcion + datos para reconocerla)
# =====================================================================
class Mascota(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mascotas_reportadas')
    nombre = models.CharField(max_length=100, blank=True)
    especie = models.CharField(max_length=10, choices=ESPECIES)
    raza = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField()
    foto = models.ImageField(upload_to='mascotas_perdidas/', blank=True, null=True)
    zona = models.CharField(max_length=150, help_text='Barrio o sector aproximado, no tu dirección exacta')
    telefono_contacto = models.CharField(max_length=30, blank=True)
    mostrar_telefono = models.BooleanField(default=False)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    # Caso 2.4: si varias personas denuncian la foto, se oculta hasta que un admin la revise
    foto_oculta = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre or 'Sin nombre'

    @property
    def foto_visible(self):
        return self.foto if (self.foto and not self.foto_oculta) else None


# =====================================================================
#  REPORTE DE PÉRDIDA  (estado_busqueda, coordenadas)
# ---------------------------------------------------------------------
#  Cada mascota publicada tiene un reporte con el estado de la búsqueda
#  y las coordenadas que usa el mapa para poner el pin.
#  tipo = 'perdida'  → foro principal (emergencias)
#  tipo = 'hallazgo' → foro de hallazgos (animales encontrados)
# =====================================================================
class ReportePerdida(models.Model):
    TIPOS = [
        ('perdida', 'Mascota perdida'),
        ('hallazgo', 'Mascota encontrada (hallazgo)'),
    ]
    ESTADOS = [
        ('activa', 'Búsqueda activa'),
        ('encontrada', 'Encontrada / Reunida'),
        ('cerrada', 'Cerrada'),
    ]
    mascota = models.OneToOneField(Mascota, on_delete=models.CASCADE, related_name='reporte')
    tipo = models.CharField(max_length=10, choices=TIPOS, default='perdida')
    estado_busqueda = models.CharField(max_length=12, choices=ESTADOS, default='activa')
    # Coordenadas del lugar donde se perdió o se encontró (null solo en reportes antiguos)
    latitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    fecha_evento = models.DateField('fecha', default=timezone.localdate)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_publicacion']  # orden cronológico: lo más nuevo primero
        verbose_name = 'reporte de pérdida'
        verbose_name_plural = 'reportes de pérdida'

    @property
    def coordenadas(self):
        if self.latitud is None or self.longitud is None:
            return None
        return {'lat': float(self.latitud), 'lng': float(self.longitud)}

    @property
    def dias_desde_evento(self):
        return max(0, (timezone.localdate() - self.fecha_evento).days)

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.mascota} ({self.get_estado_busqueda_display()})'


# =====================================================================
#  DENUNCIAS  (caso 2.4: fotos o contenido indebido)
# =====================================================================
class Denuncia(models.Model):
    MOTIVOS = [
        ('foto', 'Foto inapropiada'),
        ('texto', 'Texto ofensivo'),
        ('falsa', 'Publicación falsa o spam'),
    ]
    reporte = models.ForeignKey(ReportePerdida, on_delete=models.CASCADE, related_name='denuncias')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='denuncias')
    motivo = models.CharField(max_length=10, choices=MOTIVOS)
    fecha = models.DateTimeField(auto_now_add=True)
    revisada = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['reporte', 'usuario'], name='una_denuncia_por_usuario'),
        ]

    def __str__(self):
        return f'{self.get_motivo_display()} — {self.reporte.mascota}'


# =====================================================================
#  ESTABLECIMIENTOS Y ADOPCIONES (hechos por el grupo, sin cambios)
# =====================================================================
class Establecimiento(models.Model):
    TIPOS = [
        ('veterinaria', 'Veterinaria'),
        ('refugio', 'Refugio / Rescate'),
        ('tienda', 'Tienda de mascotas'),
    ]
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=30, blank=True)
    horario = models.CharField(max_length=150, blank=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre


class Adopcion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mascotas_adopcion')
    nombre = models.CharField(max_length=100)
    especie = models.CharField(max_length=10, choices=ESPECIES)
    edad_aproximada = models.CharField(max_length=50, blank=True)
    descripcion = models.TextField()
    foto = models.ImageField(upload_to='adopciones/', blank=True, null=True)
    zona = models.CharField(max_length=150)
    disponible = models.BooleanField(default=True)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


# =====================================================================
#  CHATS  (conversación entre quien publicó y quien tiene información)
# =====================================================================
class Conversacion(models.Model):
    reporte = models.ForeignKey(ReportePerdida, on_delete=models.CASCADE, related_name='conversaciones')
    interesado = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversaciones_iniciadas')
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-actualizada']
        verbose_name_plural = 'conversaciones'
        constraints = [
            models.UniqueConstraint(fields=['reporte', 'interesado'], name='una_conversacion_por_reporte_y_usuario'),
        ]

    @property
    def dueno(self):
        return self.reporte.mascota.usuario

    def participa(self, usuario):
        return usuario.id in (self.dueno.id, self.interesado_id)

    def otro(self, usuario):
        return self.interesado if usuario.id == self.dueno.id else self.dueno

    def __str__(self):
        return f'Chat sobre {self.reporte.mascota} con {self.interesado}'


class Mensaje(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mensajes')
    texto = models.TextField(max_length=1000)
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f'{self.autor}: {self.texto[:30]}'
