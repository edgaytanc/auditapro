# Generated by Django 5.0.6 on 2024-11-13 18:01

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('audits', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AppointmentNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='AuditMarks',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('verbose_name', models.CharField(blank=True, max_length=255, null=True)),
                ('alpha2_code', models.CharField(max_length=2, unique=True)),
                ('alpha3_code', models.CharField(max_length=3, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='CurrentStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('verbose_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Months',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Reference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='AuditTimeSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_days', models.DurationField()),
                ('worked_days', models.DurationField()),
                ('differences', models.DurationField(blank=True, null=True)),
                ('observations', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('appointment_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_time_summary_appointment_number', to='tools.appointmentnumber')),
                ('assigned_auditor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_time_summary_assigned_auditor', to=settings.AUTH_USER_MODEL)),
                ('audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_time_summary_audit', to='audits.audit')),
                ('auditor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit_time_summary_auditor', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CurrencyType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('currency', models.CharField(max_length=10)),
                ('code', models.CharField(default='', max_length=4, unique=True)),
                ('country', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='currencies', to='tools.country')),
            ],
        ),
        migrations.CreateModel(
            name='Activity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('total_days', models.DurationField()),
                ('observations', models.TextField(blank=True, null=True)),
                ('audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='audit', to='audits.audit')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_by', to=settings.AUTH_USER_MODEL)),
                ('appointment_number', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_appointment_number', to='tools.appointmentnumber')),
                ('current_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_current_status', to='tools.currentstatus')),
                ('month', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='month', to='tools.months')),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activity_reference', to='tools.reference')),
            ],
        ),
        migrations.CreateModel(
            name='SummaryHoursWorked',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total_scheduled_hours', models.DurationField()),
                ('total_hours_worked', models.DurationField()),
                ('differences', models.DurationField(blank=True, null=True)),
                ('observations', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='summary_hours_audit', to='audits.audit')),
                ('auditor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='summary_hours_auditor', to=settings.AUTH_USER_MODEL)),
                ('month', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='summary_hours_month', to='tools.months')),
            ],
        ),
        migrations.CreateModel(
            name='WorkingPapersStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('working_papers', models.CharField(max_length=255)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('observations', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('audit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='working_papers_audit', to='audits.audit')),
                ('auditor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='working_papers_auditor', to=settings.AUTH_USER_MODEL)),
                ('current_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='working_papers_statuscurrent_status', to='tools.currentstatus')),
                ('reference', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='working_papers_status_reference', to='tools.reference')),
            ],
        ),
    ]
