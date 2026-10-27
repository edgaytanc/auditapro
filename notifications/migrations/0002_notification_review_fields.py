from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


# Esta migracion reconcilia el esquema existente sin borrar datos.
# En la base actual puede existir reviewed_at (y/o reviewed_by_id) aunque
# Django nunca haya registrado esta migracion. Solo se agregan las columnas
# que realmente faltan.


def _column_names(schema_editor, table_name):
    return {
        column.name
        for column in schema_editor.connection.introspection.get_table_description(
            schema_editor.connection.cursor(), table_name
        )
    }


def _add_column_if_missing(schema_editor, table_name, column_name, sql_type):
    columns = _column_names(schema_editor, table_name)
    if column_name in columns:
        return

    q_table = schema_editor.quote_name(table_name)
    q_column = schema_editor.quote_name(column_name)
    schema_editor.execute(
        f"ALTER TABLE {q_table} ADD COLUMN {q_column} {sql_type}"
    )


def ensure_review_columns(apps, schema_editor):
    table_name = "notifications_notification"
    connection = schema_editor.connection

    if not connection.introspection.table_names():
        # La tabla debe venir de 0001_initial. Si no existe, dejamos que Django
        # falle de forma explicita en vez de crear una tabla incorrecta.
        raise RuntimeError(
            "No existe la tabla notifications_notification. "
            "La migracion 0001_initial debe estar aplicada antes de continuar."
        )

    if table_name not in connection.introspection.table_names():
        raise RuntimeError(
            "No existe la tabla notifications_notification. "
            "La migracion 0001_initial debe estar aplicada antes de continuar."
        )

    vendor = connection.vendor

    # reviewed_at
    if vendor == "postgresql":
        reviewed_at_type = "timestamp with time zone NULL"
    elif vendor == "mysql":
        reviewed_at_type = "datetime(6) NULL"
    else:
        # SQLite: DateTimeField se almacena como datetime/texto.
        reviewed_at_type = "datetime NULL"
    _add_column_if_missing(schema_editor, table_name, "reviewed_at", reviewed_at_type)

    # review_status: las opciones son una validacion de Django, no una
    # restriccion necesaria de la base de datos.
    if vendor == "postgresql":
        review_status_type = "varchar(20) NOT NULL DEFAULT 'pending'"
    else:
        review_status_type = "varchar(20) NOT NULL DEFAULT 'pending'"
    _add_column_if_missing(
        schema_editor, table_name, "review_status", review_status_type
    )

    # reviewed_by es una FK de Django y, por convencion, su columna fisica
    # es reviewed_by_id. Si ya existe se conserva exactamente como esta.
    if vendor == "postgresql":
        reviewed_by_type = "bigint NULL"
    else:
        reviewed_by_type = "bigint NULL"
    _add_column_if_missing(
        schema_editor, table_name, "reviewed_by_id", reviewed_by_type
    )

    # JSONField sobre SQLite se persiste como TEXT; sobre PostgreSQL como
    # jsonb y sobre MySQL como JSON. Usamos una representacion compatible
    # con el esquema fisico actual y dejamos la conversion a Django.
    if vendor == "postgresql":
        review_meta_type = "jsonb NOT NULL DEFAULT '{}'::jsonb"
    elif vendor == "mysql":
        review_meta_type = "json NOT NULL"
    else:
        review_meta_type = "text NOT NULL DEFAULT '{}'"
    _add_column_if_missing(
        schema_editor, table_name, "review_meta", review_meta_type
    )


def noop_reverse(apps, schema_editor):
    # No eliminamos columnas durante reverse: algunas pueden haber existido
    # antes de esta migracion y no debemos destruir datos de produccion.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_review_columns, noop_reverse),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="notification",
                    name="review_meta",
                    field=models.JSONField(blank=True, default=dict),
                ),
                migrations.AddField(
                    model_name="notification",
                    name="review_status",
                    field=models.CharField(
                        choices=[
                            ("pending", "Pendiente"),
                            ("approved", "Aprobada"),
                            ("rejected", "Rechazada"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                migrations.AddField(
                    model_name="notification",
                    name="reviewed_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="notification",
                    name="reviewed_by",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
