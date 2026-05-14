from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('chat', '0002_message_media'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationHiddenForUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'conversation',
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name='hidden_entries',
                        to='chat.conversation',
                    ),
                ),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name='hidden_chat_conversations',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name='conversationhiddenforuser',
            constraint=models.UniqueConstraint(
                fields=('conversation', 'user'),
                name='chat_convhidden_conversation_user_uniq',
            ),
        ),
    ]
