# Generated by Django 5.0.6 on 2024-11-18 18:38

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tools', '0005_months_days_alter_months_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitytotaldayspermonth',
            name='year',
            field=models.PositiveSmallIntegerField(default=2024),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='activitytotaldayspermonth',
            name='month',
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AlterField(
            model_name='activitytotaldayspermonth',
            name='total_days',
            field=models.DurationField(default=datetime.timedelta(0), editable=False),
        ),
    ]