from django.db import migrations

def add_superadmin_role(apps, schema_editor):
    Roles = apps.get_model('users', 'Roles')
    # Verificar si el rol ya existe para evitar duplicados
    if not Roles.objects.filter(name="superadmin").exists():
        Roles.objects.create(name="superadmin", verbose_name="Super Administrador")

def remove_superadmin_role(apps, schema_editor):
    Roles = apps.get_model('users', 'Roles')
    Roles.objects.filter(name="superadmin").delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),  # Ajustar esta dependencia según la última migración de la app users
    ]

    operations = [
        migrations.RunPython(add_superadmin_role, remove_superadmin_role),
    ]
