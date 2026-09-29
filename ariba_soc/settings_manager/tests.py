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


class AlertAggregationSettingTest(TestCase):
    def test_singleton_load(self):
        from .models import AlertAggregationSetting
        s1 = AlertAggregationSetting.load()
        s2 = AlertAggregationSetting.load()
        self.assertEqual(s1.pk, s2.pk)
        self.assertTrue(s1.is_enabled)
        self.assertEqual(s1.window_minutes, 15)

    def test_generate_aggregation_key(self):
        from .models import AlertAggregationSetting
        setting = AlertAggregationSetting.load()
        setting.group_by_rule = True
        setting.group_by_agent = True
        setting.group_by_source_ip = True
        setting.group_by_destination_ip = False
        setting.group_by_username = False
        setting.save()

        key1 = setting.generate_aggregation_key({
            'rule_id': '100001',
            'agent_id': 'agent-01',
            'source_ip': '10.0.0.1',
            'destination_ip': '10.0.0.2',
            'username': 'alice',
        })
        key2 = setting.generate_aggregation_key({
            'rule_id': '100001',
            'agent_id': 'agent-01',
            'source_ip': '10.0.0.1',
            'destination_ip': '10.0.0.99',  # Different dst_ip, but group_by_destination_ip is False
            'username': 'bob',             # Different user, but group_by_username is False
        })
        self.assertEqual(key1, key2)

        key3 = setting.generate_aggregation_key({
            'rule_id': '100001',
            'agent_id': 'agent-01',
            'source_ip': '10.0.0.5',        # Different src_ip
        })
        self.assertNotEqual(key1, key3)

    def test_aggregation_views_access_and_toggle(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from .models import AlertAggregationSetting

        user = User.objects.create_superuser('adminuser', 'admin@example.com', 'adminpass')
        self.client.force_login(user)

        # GET settings page
        url = reverse('settings:aggregation')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # POST toggle
        toggle_url = reverse('settings:aggregation_toggle')
        resp = self.client.post(toggle_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['is_enabled'])

        setting = AlertAggregationSetting.load()
        self.assertFalse(setting.is_enabled)



