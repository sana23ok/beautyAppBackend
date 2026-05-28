"""Conversation helpers with two participants."""

from django.contrib.auth.models import User
from django.test import TestCase

from chat.models import Conversation


class ConversationOtherParticipantTests(TestCase):
    def test_get_other_participant(self):
        u1 = User.objects.create_user(username='a', email='a@example.com', password='x')
        u2 = User.objects.create_user(username='b', email='b@example.com', password='x')
        conv = Conversation.objects.create()
        conv.participants.add(u1, u2)

        self.assertEqual(conv.get_other_participant(u1).pk, u2.pk)
        self.assertEqual(conv.get_other_participant(u2).pk, u1.pk)
