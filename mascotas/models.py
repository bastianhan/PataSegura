from django.db import models
from django.contrib.auth.models import User

ESPECIES = [
    ('perro', 'Perro'),
    ('gato', 'Gato'),
    ('otro', 'Otro'),
]


class Mascota(models.Model):
    ESTADOS = [
        ('perdida', 'Perdida'),
        ('encontrada', 'Encontrada / Reunida'),
    ]
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mascotas_reportadas')
    nombre = models.CharField(max_length=100, blank=True)
    especie = models.CharField(max_length=10, choices=ESPECIES)
    raza = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField()
    foto = models.ImageField(upload_to='mascotas_perdidas/', blank=True, null=True)
    zona = models.CharField(max_length=150, help_text='Barrio o sector aproximado, no tu dirección exacta')
    estado = models.CharField(max_length=15, choices=ESTADOS, default='perdida')
    telefono_contacto = models.CharField(max_length=30, blank=True)
    mostrar_telefono = models.BooleanField(default=False)
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nombre or "Sin nombre"} ({self.get_estado_display()})'

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
    