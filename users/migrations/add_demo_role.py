from django.db import migrations

def add_demo_role(apps, schema_editor):
    Roles = apps.get_model('users', 'Roles')
    # Verificar si el rol ya existe
    if not Roles.objects.filter(name='demo').exists():
        Roles.objects.create(name='demo', verbose_name='Usuario Demo')

def remove_demo_role(apps, schema_editor):
    Roles = apps.get_model('users', 'Roles')
    Roles.objects.filter(name='demo').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_user_deleted_at_user_is_deleted'),  # Ajusta esto según la última migración
    ]

    operations = [
        migrations.RunPython(add_demo_role, remove_demo_role),
    ]
