"""If ``table masters_masterservice already exists`` but migrate retries CreateModel:
``python manage.py migrate masters 0006_masterservice --fake`` (then ``migrate``)."""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0005_masterweektimetable'),
    ]

    operations = [
        migrations.CreateModel(
            name='MasterService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('duration_minutes', models.PositiveIntegerField(default=0)),
                ('master', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='services', to='masters.master')),
            ],
            options={
                'ordering': ['id'],
            },
        ),
    ]
