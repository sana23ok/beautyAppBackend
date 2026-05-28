"""Expiry logic for email verification codes."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from users.models import EmailVerificationCode


class EmailVerificationExpiryTests(TestCase):
    def test_not_expired_when_future(self):
        rec = EmailVerificationCode.objects.create(
            email='a@example.com',
            code_hash='0' * 64,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertFalse(rec.is_expired())

    def test_expired_when_past(self):
        rec = EmailVerificationCode.objects.create(
            email='b@example.com',
            code_hash='1' * 64,
            expires_at=timezone.now() - timedelta(seconds=30),
        )
        self.assertTrue(rec.is_expired())
