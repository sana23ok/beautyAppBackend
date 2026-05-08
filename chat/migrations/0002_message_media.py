from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='message_type',
            field=models.CharField(
                choices=[('text', 'text'), ('image', 'image'), ('video', 'video')],
                default='text',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='media_url',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='message',
            name='text',
            field=models.TextField(blank=True, default=''),
        ),
    ]
