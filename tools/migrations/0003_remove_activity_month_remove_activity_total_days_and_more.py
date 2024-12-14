# Generated by Django 5.0.6 on 2024-11-15 19:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tools', '0002_alter_audittimesummary_appointment_number_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='month',
        ),
        migrations.RemoveField(
            model_name='activity',
            name='total_days',
        ),
        migrations.CreateModel(
            name='ActivityTotalDaysPerMonth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_days', models.DurationField(blank=True, default=True, editable=False, null=True)),
                ('activity', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_total_days_per_month_activity', to='tools.activity')),
                ('month', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_total_days_per_month_month', to='tools.months')),
            ],
        ),
    ]
