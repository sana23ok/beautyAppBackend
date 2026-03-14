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
        return self.participants.exclude(id=user.id).first()


class Message(models.Model):
    """A single message in a conversation."""
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
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username}: {self.text[:30]}..."
