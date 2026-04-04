# Generated manually for MasterWeekTimetable

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0004_alter_master_city_alter_master_specialization'),
    ]

    operations = [
        migrations.CreateModel(
            name='MasterWeekTimetable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField(db_index=True)),
                ('monday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('tuesday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('wednesday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('thursday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('friday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('saturday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('sunday_hours', models.CharField(blank=True, default='', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'master',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='week_timetables',
                        to='masters.master',
                    ),
                ),
            ],
            options={
                'ordering': ['week_start'],
            },
        ),
        migrations.AddConstraint(
            model_name='masterweektimetable',
            constraint=models.UniqueConstraint(fields=('master', 'week_start'), name='unique_master_week_start'),
        ),
    ]
