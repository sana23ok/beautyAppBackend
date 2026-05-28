"""Unit tests for CSV / lookup helpers (no DB)."""

from django.test import SimpleTestCase

from appearance_test.recommendations_lookup import (
    build_api_payload,
    split_list_field,
)


class SplitListFieldTests(SimpleTestCase):
    def test_empty(self):
        self.assertEqual(split_list_field(''), [])
        self.assertEqual(split_list_field('   '), [])

    def test_simple_csv(self):
        self.assertEqual(
            split_list_field('Teal Green, Crimson'),
            ['Teal Green', 'Crimson'],
        )

    def test_comma_inside_parentheses_kept(self):
        s = 'Navy Blue, Earth Tones(Camel, Ivory, Taupe)'
        parts = split_list_field(s)
        self.assertEqual(len(parts), 2)


class BuildApiPayloadTests(SimpleTestCase):
    def test_contains_inputs_and_extended_keys(self):
        row = {
            'Recommended Clothing Colors': '',
            'Avoid Clothing Colors': '',
            'Seasonal Color Type': '',
            'Recommended Clothing Color Wheel Region': 'Cool',
            'Fabric Nature': 'cotton',
            'Do Exaggerate': '',
            'Recommended Fitting Style': 'straight',
            'Recommended Materials': '',
            'Recommended Patterns': '',
            'Recommended Jewelry Metal': '',
            'Recommended Shoes': '',
            'Avoid Clothing Color Wheel Region': '',
            'dont_colours': '',
            'do_colours': '',
            "Don't Exaggerate": '',
        }
        inputs = {
            'hair_color': 'Brown',
            'eyes_color': 'Green',
            'skin_tone': 'Fair',
            'undertone': 'warm',
            'torso_length': 'Balanced',
            'body_proportion': 'Pear',
        }
        out = build_api_payload(row, inputs)
        self.assertIn('inputs_summary', out)
        self.assertIn('analysis_result', out)
        self.assertIn('extended_recommendations', out)
        self.assertIn('Pear', out['inputs_summary'])
        self.assertEqual(out['analysis_result']['body_type']['shape'], 'Pear')
