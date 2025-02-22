# Generated by Django 5.0.6 on 2024-11-13 18:01

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('company', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_users', models.ManyToManyField(blank=True, related_name='assigned_users', to=settings.AUTH_USER_MODEL)),
                ('audit_manager', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_manager', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
