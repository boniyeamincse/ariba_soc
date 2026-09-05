from django.test import TestCase
from .services import map_level_to_severity


class MapLevelToSeverityTest(TestCase):
    def test_critical(self):
        self.assertEqual(map_level_to_severity(12), 'Critical')
        self.assertEqual(map_level_to_severity(15), 'Critical')

    def test_high(self):
        self.assertEqual(map_level_to_severity(8), 'High')
        self.assertEqual(map_level_to_severity(11), 'High')

    def test_medium(self):
        self.assertEqual(map_level_to_severity(4), 'Medium')
        self.assertEqual(map_level_to_severity(7), 'Medium')

    def test_low(self):
        self.assertEqual(map_level_to_severity(1), 'Low')
        self.assertEqual(map_level_to_severity(3), 'Low')

    def test_informational(self):
        self.assertEqual(map_level_to_severity(0), 'Informational')
