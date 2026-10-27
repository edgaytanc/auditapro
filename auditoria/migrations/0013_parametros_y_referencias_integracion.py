# Migracion acumulativa para Sistema_audita (mantiene 0012_auditfinding_and_more).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('auditoria', '0012_auditfinding_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ParametrosAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anio_actual', models.PositiveIntegerField(blank=True, null=True)),
                ('anio_anterior', models.PositiveIntegerField(blank=True, null=True)),
                ('anios_manuales', models.BooleanField(default=False)),
                ('anio_actual_excel', models.PositiveIntegerField(blank=True, null=True)),
                ('anio_anterior_excel', models.PositiveIntegerField(blank=True, null=True)),
                ('fecha_corte1_excel', models.DateField(blank=True, null=True)),
                ('fecha_corte2_excel', models.DateField(blank=True, null=True)),
                ('fecha_corte3_excel', models.DateField(blank=True, null=True)),
                ('fecha_corte_actual_excel', models.DateField(blank=True, null=True)),
                ('ingresos_totales_excel', models.FloatField(blank=True, null=True)),
                ('utilidad_antes_impuestos_excel', models.FloatField(blank=True, null=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('audit', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='parametros', to='audits.audit')),
            ],
            options={'verbose_name': 'Parámetros de auditoría', 'verbose_name_plural': 'Parámetros de auditorías', 'db_table': 'auditoria_parametrosauditoria'},
        ),
        migrations.CreateModel(
            name='ReferenciaPapelTrabajo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('carpeta', models.CharField(max_length=500)),
                ('archivo', models.CharField(max_length=255)),
                ('referencia', models.CharField(max_length=50)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referencias_papeles', to='audits.audit')),
            ],
            options={'verbose_name': 'Referencia de papel de trabajo', 'verbose_name_plural': 'Referencias de papeles de trabajo', 'db_table': 'auditoria_referenciapapeltrabajo'},
        ),
        migrations.AddConstraint(model_name='referenciapapeltrabajo', constraint=models.UniqueConstraint(fields=('audit', 'carpeta', 'archivo'), name='unique_referencia_por_papel')),
    ]
