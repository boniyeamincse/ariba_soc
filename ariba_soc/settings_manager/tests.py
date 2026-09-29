from django.test import TestCase
from .models import SystemSetting, AlarmSetting, AlarmSystemSetting


class SystemSettingTest(TestCase):
    def test_get_setting_default(self):
        val = SystemSetting.get_setting('nonexistent', 'default_val')
        self.assertEqual(val, 'default_val')

    def test_get_setting_stored(self):
        SystemSetting.objects.create(key='test_key', value='test_val')
        val = SystemSetting.get_setting('test_key', 'default')
        self.assertEqual(val, 'test_val')


class AlarmSettingTest(TestCase):
    def test_alarm_defaults_seeded(self):
        severities = list(AlarmSetting.objects.values_list('severity', flat=True))
        self.assertEqual(severities, ['Low', 'Medium', 'High', 'Critical'])
        self.assertTrue(AlarmSystemSetting.load().is_enabled)

    def test_alarm_severity_enabled_respects_master_switch(self):
        alarm_system = AlarmSystemSetting.load()
        alarm_system.is_enabled = True
        alarm_system.save(update_fields=['is_enabled', 'updated_at'])
        self.assertTrue(AlarmSetting.severity_enabled('Critical'))
        alarm_system.is_enabled = False
        alarm_system.save(update_fields=['is_enabled', 'updated_at'])
        self.assertFalse(AlarmSetting.severity_enabled('Critical'))
