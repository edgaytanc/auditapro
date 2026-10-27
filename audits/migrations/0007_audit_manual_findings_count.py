from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('audits', '0006_audit_activa_financiera_audit_activa_interna_and_more')]
    operations = [
        migrations.AddField(
            model_name='audit',
            name='manual_findings_count',
            field=models.PositiveIntegerField(null=True, blank=True, verbose_name='Número informado de hallazgos'),
        ),
    ]
