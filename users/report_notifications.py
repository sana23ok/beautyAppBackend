"""Notify staff users about a report by creating a DM from the reporter to each staff account."""

from django.contrib.auth import get_user_model

User = get_user_model()


def notify_staff_by_dm(reporter, message_text: str) -> None:
    """
    For each user with is_staff=True (except reporter), ensure a 1:1 conversation exists
    and append a text message from reporter. Used when a report includes free-form text.
    """
    text = (message_text or '').strip()
    if not text:
        return

    from chat.models import Conversation, Message

    staff = (
        User.objects.filter(is_staff=True)
        .exclude(pk=reporter.pk)
        .order_by('id')
    )
    for moderator in staff:
        conv = (
            Conversation.objects.filter(participants=reporter)
            .filter(participants=moderator)
            .first()
        )
        if not conv:
            conv = Conversation.objects.create()
            conv.participants.add(reporter, moderator)
        Message.objects.create(conversation=conv, sender=reporter, text=text)
        conv.save()
