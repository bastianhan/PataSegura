from django.contrib import admin
from .models import (Mascota, Establecimiento, Adopcion, PerfilUsuario, ReportePerdida,
                     Conversacion, Mensaje, Denuncia)


class ReporteInline(admin.StackedInline):
    model = ReportePerdida
    extra = 0


@admin.register(Mascota)
class MascotaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'especie', 'zona', 'usuario', 'foto_oculta', 'fecha_publicacion')
    list_filter = ('especie', 'foto_oculta')
    search_fields = ('nombre', 'descripcion', 'zona')
    inlines = [ReporteInline]
    actions = ['eliminar_foto', 'mostrar_foto']

    @admin.action(description='Eliminar la foto (contenido indebido)')
    def eliminar_foto(self, request, queryset):
        for m in queryset:
            if m.foto:
                m.foto.delete(save=False)
            m.foto_oculta = False
            m.save()
            Denuncia.objects.filter(reporte__mascota=m).update(revisada=True)

    @admin.action(description='La foto está bien: volver a mostrarla')
    def mostrar_foto(self, request, queryset):
        queryset.update(foto_oculta=False)
        Denuncia.objects.filter(reporte__mascota__in=queryset).update(revisada=True)


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ('reporte', 'motivo', 'usuario', 'fecha', 'revisada')
    list_filter = ('revisada', 'motivo')


@admin.register(ReportePerdida)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('mascota', 'tipo', 'estado_busqueda', 'latitud', 'longitud', 'fecha_evento')
    list_filter = ('tipo', 'estado_busqueda')


@admin.register(PerfilUsuario)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'telefono', 'comuna', 'mostrar_telefono')


class MensajeInline(admin.TabularInline):
    model = Mensaje
    extra = 0


@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'actualizada')
    inlines = [MensajeInline]


admin.site.register(Establecimiento)
admin.site.register(Adopcion)
