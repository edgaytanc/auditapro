from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="CupoConsultasIA",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("restantes", models.PositiveIntegerField(default=5)),
                ("realizadas", models.PositiveIntegerField(default=0)),
                ("version_cupo", models.PositiveIntegerField(default=0)),
                ("actualizado", models.DateTimeField(auto_now=True)),
                ("usuario", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="cupo_audita_analisis", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Cupo de Audita Análisis", "verbose_name_plural": "Cupos de Audita Análisis"},
        ),
    ]
