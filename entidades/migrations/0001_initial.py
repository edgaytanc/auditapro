# Generated by Django 4.1.7 on 2024-04-02 05:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Entidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre de Entidad')),
                ('auditores', models.ManyToManyField(related_name='entidades_auditadas', to=settings.AUTH_USER_MODEL)),
                ('creador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entidades_creadas', to=settings.AUTH_USER_MODEL)),
                ('supervisores', models.ManyToManyField(related_name='entidades_supervisadas', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
