from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """A conversation between two users."""
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        usernames = ', '.join(u.username for u in self.participants.all()[:2])
        return f"Conversation({self.id}): {usernames}"

    def get_other_participant(self, user):
        """Return the other participant in a two-person conversation."""
        # Iterate .all() so prefetched participants (with select_related profile/master) stay cached.
        # .exclude().first() can hit the DB with a plain User queryset and drop prefetch optimizations.
        for p in self.participants.all():
            if p.id != user.id:
                return p
        return None


class Message(models.Model):
    """A single message in a conversation."""
    MESSAGE_TEXT = 'text'
    MESSAGE_IMAGE = 'image'
    MESSAGE_VIDEO = 'video'

    MESSAGE_TYPE_CHOICES = (
        (MESSAGE_TEXT, MESSAGE_TEXT),
        (MESSAGE_IMAGE, MESSAGE_IMAGE),
        (MESSAGE_VIDEO, MESSAGE_VIDEO),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
    )
    message_type = models.CharField(
        max_length=10,
        choices=MESSAGE_TYPE_CHOICES,
        default=MESSAGE_TEXT,
    )
    text = models.TextField(blank=True, default='')
    media_url = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        preview = (self.text[:30] if self.text else self.media_url[:30]) or '…'
        return f"Message from {self.sender.username}: {preview}..."
