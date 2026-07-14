from django.test import TestCase
from .models import SystemSetting


class SystemSettingTest(TestCase):
    def test_get_setting_default(self):
        val = SystemSetting.get_setting('nonexistent', 'default_val')
        self.assertEqual(val, 'default_val')

    def test_get_setting_stored(self):
        SystemSetting.objects.create(key='test_key', value='test_val')
        val = SystemSetting.get_setting('test_key', 'default')
        self.assertEqual(val, 'test_val')
