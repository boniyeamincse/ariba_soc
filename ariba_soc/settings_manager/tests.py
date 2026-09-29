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


class AlertSuppressionRuleTest(TestCase):
    def test_rule_matches_and_expiration(self):
        from datetime import timedelta
        from django.utils import timezone
        from .models import AlertSuppressionRule

        rule = AlertSuppressionRule.objects.create(
            name='Mute scanner',
            rule_id='5710',
            source_ip='192.168.1.100',
            action='AUTO_CLOSE',
            is_active=True,
        )

        # Matches identical alert
        self.assertTrue(rule.matches({'rule_id': '5710', 'source_ip': '192.168.1.100'}))

        # Does not match different IP
        self.assertFalse(rule.matches({'rule_id': '5710', 'source_ip': '192.168.1.101'}))

        # Does not match if inactive
        rule.is_active = False
        rule.save()
        self.assertFalse(rule.matches({'rule_id': '5710', 'source_ip': '192.168.1.100'}))

        # Does not match if expired
        rule.is_active = True
        rule.expires_at = timezone.now() - timedelta(minutes=5)
        rule.save()
        self.assertTrue(rule.is_expired)
        self.assertFalse(rule.matches({'rule_id': '5710', 'source_ip': '192.168.1.100'}))

    def test_suppression_views_crud_and_toggle(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from .models import AlertSuppressionRule

        user = User.objects.create_superuser('soclead', 'lead@example.com', 'password')
        self.client.force_login(user)

        # List
        resp = self.client.get(reverse('settings:suppression_rules'))
        self.assertEqual(resp.status_code, 200)

        # Create
        create_resp = self.client.post(reverse('settings:suppression_rules'), {
            'name': 'Suppress Test Rule',
            'action': 'AUTO_CLOSE',
            'rule_id': '100045',
            'source_ip': '10.10.10.10',
            'reason': 'Authorized scan',
            'is_active': 'on',
        })
        self.assertEqual(create_resp.status_code, 302)
        rule = AlertSuppressionRule.objects.get(name='Suppress Test Rule')
        self.assertEqual(rule.rule_id, '100045')
        self.assertEqual(rule.created_by, user)

        # Toggle via AJAX
        toggle_resp = self.client.post(
            reverse('settings:suppression_rule_toggle', args=[rule.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.json()['is_active'])

        # Delete
        del_resp = self.client.post(reverse('settings:suppression_rule_delete', args=[rule.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(AlertSuppressionRule.objects.filter(id=rule.id).exists())




