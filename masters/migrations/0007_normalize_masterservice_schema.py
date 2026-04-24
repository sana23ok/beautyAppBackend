from django.db import migrations


class Migration(migrations.Migration):
    """No-op; kept so migration history and dependency order stay unchanged."""

    dependencies = [
        ('masters', '0006_masterservice'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, migrations.RunPython.noop),
    ]
