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


class SettingsAccessAndAdminTest(TestCase):
    def test_check_settings_access_superuser(self):
        from django.contrib.auth.models import User
        from .views import _check_settings_access
        su = User.objects.create_superuser('superadmin', 'su@test.com', 'password')
        self.assertTrue(_check_settings_access(su))

    def test_check_settings_access_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser
        from .views import _check_settings_access
        self.assertFalse(_check_settings_access(AnonymousUser()))

    def test_admin_registration(self):
        from django.contrib import admin
        from .models import AlarmSetting, AlarmSystemSetting, IOCEnrichmentSetting
        from incidents.models import Incident, IncidentAlert, IncidentTimeline, IncidentNote
        from vulnerabilities.models import VulnerabilityCase, VulnerabilityAuditLog

        self.assertIn(AlarmSetting, admin.site._registry)
        self.assertIn(AlarmSystemSetting, admin.site._registry)
        self.assertIn(IOCEnrichmentSetting, admin.site._registry)
        self.assertIn(Incident, admin.site._registry)
        self.assertIn(IncidentAlert, admin.site._registry)
        self.assertIn(IncidentTimeline, admin.site._registry)
        self.assertIn(IncidentNote, admin.site._registry)
        self.assertIn(VulnerabilityCase, admin.site._registry)
        self.assertIn(VulnerabilityAuditLog, admin.site._registry)

