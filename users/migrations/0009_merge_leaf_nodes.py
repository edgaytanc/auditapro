from django.db import migrations


class Migration(migrations.Migration):
    """Une las dos hojas 0008 (merge_local y merge_20260226_0040) para que
    `migrate` y la suite de pruebas funcionen en una base de datos nueva."""

    dependencies = [
        ("users", "0008_merge_20260226_0040"),
        ("users", "0008_merge_local"),
    ]

    operations = []
