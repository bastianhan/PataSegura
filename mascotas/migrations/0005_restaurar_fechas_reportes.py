from django.db import migrations
from django.db.models import OuterRef, Subquery


def restaurar_fechas(apps, schema_editor):
    Mascota = apps.get_model('mascotas', 'Mascota')
    Reporte = apps.get_model('mascotas', 'ReportePerdida')
    fecha = Mascota.objects.using(schema_editor.connection.alias).filter(pk=OuterRef('mascota_id')).values('fecha_publicacion')[:1]
    Reporte.objects.using(schema_editor.connection.alias).update(fecha_publicacion=Subquery(fecha))


class Migration(migrations.Migration):
    dependencies = [('mascotas', '0004_denuncias_y_fotos_ocultas')]
    operations = [migrations.RunPython(restaurar_fechas, migrations.RunPython.noop)]
