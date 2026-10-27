from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("users", "0009_user_auditoria_interna")]
    operations = [migrations.CreateModel(
        name="FinancialDashboardIdentity",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
            ("scope_key", models.CharField(default="general", max_length=64)),
            ("company_name", models.CharField(max_length=255)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="financial_dashboard_identities", to=settings.AUTH_USER_MODEL)),
        ],
        options={"constraints": [models.UniqueConstraint(fields=("user", "scope_key"), name="unique_financial_dashboard_user_scope")]},
    )]
