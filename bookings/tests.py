"""Unit tests for working-hours parsing helpers (no DB)."""

from django.test import SimpleTestCase

from bookings.serializers import _bounds_from_hours


class BoundsFromHoursTests(SimpleTestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(_bounds_from_hours(None))
        self.assertIsNone(_bounds_from_hours(''))
        self.assertIsNone(_bounds_from_hours('   '))

    def test_single_number_returns_none(self):
        self.assertIsNone(_bounds_from_hours('9'))

    def test_inverted_range_returns_none(self):
        self.assertIsNone(_bounds_from_hours('18-9'))

    def test_parses_simple_range(self):
        self.assertEqual(_bounds_from_hours('9-17'), (9, 17))

    def test_extracts_first_two_digits_from_text(self):
        self.assertEqual(_bounds_from_hours('Mon 10 till 14'), (10, 14))

    def test_full_day_midnight_to_end(self):
        self.assertEqual(_bounds_from_hours('0-24'), (0, 24))
