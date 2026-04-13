from django.db import migrations


def normalize_masterservice_schema(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return

    table_name = 'masters_masterservice'
    old_table_name = f'{table_name}_old'
    index_name = 'masters_masterservice_master_id_6c320147'

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        columns = [row[1] for row in cursor.fetchall()]

    if 'sort_order' not in columns:
        return

    MasterService = apps.get_model('masters', 'MasterService')

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'ALTER TABLE "{table_name}" RENAME TO "{old_table_name}"')
        cursor.execute(f'DROP INDEX IF EXISTS "{index_name}"')

    schema_editor.create_model(MasterService)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f'''
            INSERT INTO "{table_name}" ("id", "name", "price", "duration_minutes", "master_id")
            SELECT "id", "name", "price", "duration_minutes", "master_id"
            FROM "{old_table_name}"
            '''
        )
        cursor.execute(f'DROP TABLE "{old_table_name}"')


class Migration(migrations.Migration):
    dependencies = [
        ('masters', '0006_masterservice'),
    ]

    operations = [
        migrations.RunPython(normalize_masterservice_schema, migrations.RunPython.noop),
    ]
