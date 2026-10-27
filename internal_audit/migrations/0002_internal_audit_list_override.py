from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("internal_audit", "0001_initial")]
    operations = [migrations.CreateModel(
        name="InternalAuditListOverride",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ("display_code", models.CharField(max_length=60, blank=True, default="")),
            ("process_area", models.CharField(max_length=255, blank=True, default="")),
            ("client", models.CharField(max_length=255, blank=True, default="")),
            ("auditor_name", models.CharField(max_length=255, blank=True, default="")),
            ("manual_progress", models.PositiveSmallIntegerField(null=True, blank=True)),
            ("manual_close_date", models.DateField(null=True, blank=True)),
            ("manual_status", models.CharField(max_length=20, blank=True, default="")),
            ("manual_risk", models.CharField(max_length=20, blank=True, default="")),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("audit", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="internal_list_override", to="audits.audit")),
        ],
    )]
