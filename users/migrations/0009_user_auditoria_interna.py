from django.db import migrations, models
from django.db.models import Q


def preserve_existing_internal_access(apps, schema_editor):
    """Respeta accesos existentes de usuarios con encargos internos previos."""
    User = apps.get_model('users', 'User')
    Audit = apps.get_model('audits', 'Audit')
    audits = Audit.objects.filter(
        Q(activa_interna=True)
        | Q(
            activa_financiera=False,
            activa_revisoria=False,
            activa_interna=False,
            tipoAuditoria='I',
        )
    )
    ids = set(audits.values_list('audit_manager_id', flat=True))
    ids.update(User.objects.filter(assigned_users__in=audits).values_list('pk', flat=True))
    if ids:
        User.objects.filter(pk__in=ids).update(auditoria_interna=True)


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0008_rolemodulepermission_and_more'),
        ('audits', '0006_audit_activa_financiera_audit_activa_interna_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='auditoria_interna',
            field=models.BooleanField(
                default=False,
                help_text='Acceso autorizado por el administrador al módulo de Auditoría Interna.',
            ),
        ),
        migrations.RunPython(preserve_existing_internal_access, migrations.RunPython.noop),
    ]
