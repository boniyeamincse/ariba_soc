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
            'status': 'APPROVED',
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


class AlertRoutingRuleTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.u1 = User.objects.create_user('router_l2_a', password='x')
        self.u1.analyst_profile.role = 'L2'
        self.u1.analyst_profile.save()
        self.u2 = User.objects.create_user('router_l2_b', password='x')
        self.u2.analyst_profile.role = 'L2'
        self.u2.analyst_profile.save()

    def _make_alert(self, **kwargs):
        from alerts.models import Alert
        data = {
            'alert_name': 'Test Alert',
            'severity': 'Critical',
            'status': 'New',
            'rule_id': '5710',
            'hostname': 'web1',
            'username': 'root',
            'source_ip': '10.0.0.5',
        }
        data.update(kwargs)
        return Alert.objects.create(**data)

    def test_matches_by_severity_and_rule(self):
        from .models import AlertRoutingRule
        rule = AlertRoutingRule.objects.create(name='Crit 5710', match_severity='Critical', match_rule_id='5710')
        self.assertTrue(rule.matches(self._make_alert()))
        self.assertFalse(rule.matches(self._make_alert(severity='Low')))
        self.assertFalse(rule.matches(self._make_alert(rule_id='1000')))

    def test_matches_source_ip_cidr(self):
        from .models import AlertRoutingRule
        rule = AlertRoutingRule.objects.create(name='CIDR', match_source_ip='10.0.0.0/24')
        self.assertTrue(rule.matches(self._make_alert(source_ip='10.0.0.200')))
        self.assertFalse(rule.matches(self._make_alert(source_ip='192.168.1.1')))

    def test_matches_requires_criteria(self):
        from .models import AlertRoutingRule
        rule = AlertRoutingRule.objects.create(name='Empty')
        self.assertFalse(rule.matches(self._make_alert()))

    def test_apply_routes_to_assignee(self):
        from .models import AlertRoutingRule
        from alerts.services import apply_routing_rules
        AlertRoutingRule.objects.create(name='To u1', match_severity='Critical', assignee=self.u1)
        alert = self._make_alert()
        matched = apply_routing_rules(alert)
        self.assertIsNotNone(matched)
        alert.refresh_from_db()
        self.assertEqual(alert.assignee, self.u1)
        self.assertEqual(alert.status, 'New')
        self.assertIsNone(alert.acknowledged_at)

    def test_apply_routes_to_least_loaded(self):
        from .models import AlertRoutingRule
        from alerts.services import apply_routing_rules
        self._make_alert(status='New', assignee=self.u1)
        AlertRoutingRule.objects.create(name='Team L2', match_severity='Critical', assign_team='L2')
        alert = self._make_alert()
        apply_routing_rules(alert)
        alert.refresh_from_db()
        self.assertEqual(alert.assignee, self.u2)
        self.assertEqual(alert.current_tier, 'L2')

    def test_stop_on_match(self):
        from .models import AlertRoutingRule
        from alerts.services import apply_routing_rules
        first = AlertRoutingRule.objects.create(name='First', priority=1, match_severity='Critical', assignee=self.u1, stop_on_match=True)
        second = AlertRoutingRule.objects.create(name='Second', priority=2, match_severity='Critical', assignee=self.u2)
        alert = self._make_alert()
        apply_routing_rules(alert)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.match_count, 1)
        self.assertEqual(second.match_count, 0)
        alert.refresh_from_db()
        self.assertEqual(alert.assignee, self.u1)

    def test_no_criteria_for_assigned_or_terminal_alert(self):
        from .models import AlertRoutingRule
        from alerts.services import apply_routing_rules
        AlertRoutingRule.objects.create(name='To u1', match_severity='Critical', assignee=self.u1)
        already = self._make_alert(assignee=self.u2)
        self.assertIsNone(apply_routing_rules(already))
        already.refresh_from_db()
        self.assertEqual(already.assignee, self.u2)

        closed = self._make_alert(status='Closed')
        self.assertIsNone(apply_routing_rules(closed))
        self.assertIsNone(closed.assignee)

    def test_ingest_pipeline_applies_routing(self):
        from .models import AlertRoutingRule
        from alerts.services import ingest_or_aggregate_alert
        AlertRoutingRule.objects.create(name='Ingest route', match_rule_id='5555', assignee=self.u1)
        alert, created = ingest_or_aggregate_alert({
            'alert_name': 'Ingest Routing Test',
            'severity': 'High',
            'status': 'New',
            'rule_id': '5555',
            'hostname': 'srv1',
            'source_ip': '10.1.1.1',
        })
        self.assertTrue(created)
        self.assertEqual(alert.assignee, self.u1)

    def test_routing_crud_flow(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from .models import AlertRoutingRule
        admin = User.objects.create_superuser('routing_admin', 'ra@example.com', 'password')
        self.client.force_login(admin)

        resp = self.client.get(reverse('settings:routing_rules'))
        self.assertEqual(resp.status_code, 200)

        create_resp = self.client.post(reverse('settings:routing_rules'), {
            'name': 'Routing CRUD Rule',
            'priority': 10,
            'is_active': 'on',
            'match_severity': 'Critical',
            'assignee': self.u1.id,
            'stop_on_match': 'on',
        })
        self.assertEqual(create_resp.status_code, 302)
        rule = AlertRoutingRule.objects.get(name='Routing CRUD Rule')
        self.assertEqual(rule.created_by, admin)

        toggle_resp = self.client.post(
            reverse('settings:routing_rule_toggle', args=[rule.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.json()['is_active'])

        del_resp = self.client.post(reverse('settings:routing_rule_delete', args=[rule.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(AlertRoutingRule.objects.filter(id=rule.id).exists())


class NotificationChannelTest(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('notif_u1', 'u1@example.com', 'x')
        self.user.analyst_profile.role = 'L1'
        self.user.analyst_profile.save()

    def test_dashboard_notification_created(self):
        from alerts.models import Notification
        from alerts.services import send_notification
        from .models import NotificationSetting
        NotificationSetting.objects.create(
            name='dash', event_type='NEW_CRITICAL', channel='DASHBOARD', recipient_user=self.user,
        )
        res = send_notification('NEW_CRITICAL', 'Subj', 'Body', link='/x/')
        self.assertEqual(res['dashboard'], 1)
        self.assertTrue(Notification.objects.filter(user=self.user, message='Body', link='/x/').exists())

    def test_email_notification_sent(self):
        from django.core import mail
        from alerts.services import send_notification
        from .models import NotificationSetting
        NotificationSetting.objects.create(
            name='mail', event_type='NEW_CRITICAL', channel='EMAIL', recipient_user=self.user,
        )
        res = send_notification('NEW_CRITICAL', 'Subject X', 'Body', link='/x/')
        self.assertEqual(res['email'], 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('u1@example.com', mail.outbox[0].to)

    def test_webhook_notification_posts(self):
        from unittest.mock import patch
        from alerts.services import send_notification
        from .models import NotificationSetting
        NotificationSetting.objects.create(
            name='slack', event_type='NEW_CRITICAL', channel='SLACK',
            webhook_url='https://hooks.example/x',
        )
        with patch('requests.post') as mock_post:
            res = send_notification('NEW_CRITICAL', 'Subj', 'Body', link='/x/')
        self.assertEqual(res['webhook'], 1)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertIn('text', kwargs['json'])

    def test_preference_disables_channel(self):
        from alerts.models import Notification
        from alerts.services import send_notification
        from .models import NotificationSetting, UserNotificationPreference
        NotificationSetting.objects.create(
            name='dash', event_type='NEW_CRITICAL', channel='DASHBOARD', recipient_user=self.user,
        )
        pref, _ = UserNotificationPreference.objects.get_or_create(user=self.user)
        pref.dashboard_enabled = False
        pref.save()
        res = send_notification('NEW_CRITICAL', 'Subj', 'Body')
        self.assertEqual(res['dashboard'], 0)
        self.assertEqual(res['skipped'], 1)
        self.assertFalse(Notification.objects.filter(user=self.user).exists())

    def test_preference_mutes_event(self):
        from alerts.services import send_notification
        from .models import NotificationSetting, UserNotificationPreference
        NotificationSetting.objects.create(
            name='dash', event_type='SLA_BREACH', channel='DASHBOARD', recipient_user=self.user,
        )
        pref, _ = UserNotificationPreference.objects.get_or_create(user=self.user)
        pref.muted_events = ['SLA_BREACH']
        pref.save()
        res = send_notification('SLA_BREACH', 'Subj', 'Body')
        self.assertEqual(res['dashboard'], 0)
        self.assertEqual(res['skipped'], 1)

    def test_preferences_view(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from .models import UserNotificationPreference
        admin = User.objects.create_superuser('pref_admin', 'pa@example.com', 'password')
        self.client.force_login(admin)
        url = reverse('settings:notification_preferences')
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {
            'dashboard_enabled': 'on',
            'email_enabled': 'on',
            'slack_enabled': 'on',
            'teams_enabled': 'on',
            'webhook_enabled': 'on',
            'muted_events': ['SLA_BREACH'],
        })
        self.assertEqual(resp.status_code, 302)
        pref = UserNotificationPreference.objects.get(user=admin)
        self.assertIn('SLA_BREACH', pref.muted_events)


class PlaybookTest(TestCase):
    def test_playbook_crud_flow(self):
        from django.contrib.auth.models import User
        from django.urls import reverse
        from .models import Playbook
        admin = User.objects.create_superuser('pb_admin', 'pb@example.com', 'password')
        self.client.force_login(admin)

        self.assertEqual(self.client.get(reverse('settings:playbook_list')).status_code, 200)

        create_resp = self.client.post(reverse('settings:playbook_list'), {
            'title': 'CRUD Playbook',
            'priority': 5,
            'is_active': 'on',
            'match_rule_id': '5710',
            'steps': 'Step one\nStep two',
        })
        self.assertEqual(create_resp.status_code, 302)
        pb = Playbook.objects.get(title='CRUD Playbook')
        self.assertEqual(pb.created_by, admin)
        self.assertEqual(pb.step_list(), ['Step one', 'Step two'])

        edit_resp = self.client.post(reverse('settings:playbook_edit', args=[pb.id]), {
            'title': 'CRUD Playbook v2',
            'priority': 6,
            'is_active': 'on',
            'match_severity': 'High',
            'steps': 'Only step',
        })
        self.assertEqual(edit_resp.status_code, 302)
        pb.refresh_from_db()
        self.assertEqual(pb.title, 'CRUD Playbook v2')
        self.assertEqual(pb.match_severity, 'High')

        toggle_resp = self.client.post(
            reverse('settings:playbook_toggle', args=[pb.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(toggle_resp.status_code, 200)
        self.assertFalse(toggle_resp.json()['is_active'])

        del_resp = self.client.post(reverse('settings:playbook_delete', args=[pb.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Playbook.objects.filter(id=pb.id).exists())






