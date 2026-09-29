from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Alert, AlertSource, AlertComment, AlertAuditLog, Notification
from accounts.models import AnalystProfile, RolePermission
from settings_manager.models import AlarmSetting, AlarmSystemSetting
from wazuh_integration.services import map_level_to_severity, normalize_alert
from .services import emit_alarm_notification


class AlertModelTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='Test', source_type='Wazuh')
        self.alert = Alert.objects.create(
            alert_name='Test Alert',
            severity='Critical',
            rule_level=12,
            alert_time=timezone.now(),
            source=self.source,
        )

    def test_update_sla_sets_due_at(self):
        self.alert.update_sla()
        self.assertIsNotNone(self.alert.sla_due_at)

    def test_update_sla_status_valid(self):
        self.alert.update_sla()
        self.assertIn(self.alert.sla_status, ['Within SLA', 'Breached', 'Near SLA breach'])

    def test_calculate_priority_critical(self):
        self.assertEqual(self.alert.calculate_priority(), 'Critical')

    def test_str_representation(self):
        self.assertIn('Critical', str(self.alert))


class AlertSourceTest(TestCase):
    def test_str(self):
        s = AlertSource.objects.create(name='Wazuh')
        self.assertEqual(str(s), 'Wazuh')


class RolePermissionTest(TestCase):
    def setUp(self):
        # RolePermission rows for every role are seeded by a migration
        # (accounts/migrations/0003_seed_role_permissions.py), so ADMIN's row
        # already exists in a fresh test DB -- update it rather than assuming
        # a clean table. can_archive is pinned False explicitly since the
        # real seed defaults grant it to ADMIN, but this test wants a known
        # not-granted permission to check the false case against.
        RolePermission.objects.update_or_create(
            role='ADMIN', defaults={'can_manage_users': True, 'can_archive': False}
        )

    def test_has_permission_true(self):
        self.assertTrue(RolePermission.has_permission('ADMIN', 'can_manage_users'))

    def test_has_permission_false(self):
        self.assertFalse(RolePermission.has_permission('ADMIN', 'can_archive'))

    def test_has_permission_no_role(self):
        self.assertFalse(RolePermission.has_permission('NONEXISTENT', 'can_view_alerts'))


class AnalystProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='analyst', password='pass')
        RolePermission.objects.update_or_create(role='L1', defaults={'can_view_alerts': True})

    def test_has_permission_delegates(self):
        profile = self.user.analyst_profile
        profile.role = 'L1'
        profile.save()
        self.assertTrue(profile.has_permission('can_view_alerts'))


class WazuhServicesTest(TestCase):
    def test_map_level_to_severity(self):
        self.assertEqual(map_level_to_severity(12), 'Critical')
        self.assertEqual(map_level_to_severity(8), 'High')
        self.assertEqual(map_level_to_severity(4), 'Medium')
        self.assertEqual(map_level_to_severity(1), 'Low')
        self.assertEqual(map_level_to_severity(0), 'Informational')


class AlarmNotificationTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='Test', source_type='Wazuh')
        AlarmSetting.objects.all().delete()
        for idx, severity in enumerate(['Low', 'Medium', 'High', 'Critical'], start=1):
            AlarmSetting.objects.create(severity=severity, is_enabled=True, sort_order=idx)
        alarm_system = AlarmSystemSetting.load()
        alarm_system.is_enabled = True
        alarm_system.is_active = False
        alarm_system.sound_file = None
        alarm_system.save(update_fields=['is_enabled', 'is_active', 'updated_at'])

        self.user = User.objects.create_user(username='analyst1', password='pass', email='analyst1@example.com')
        self.profile = self.user.analyst_profile
        self.profile.role = 'SOC_ENG'
        self.profile.save()

    def test_emit_alarm_notification_creates_dashboard_notification(self):
        Alert.objects.bulk_create([
            Alert(
                alert_name='Critical Alert',
                severity='Critical',
                rule_level=12,
                alert_time=timezone.now(),
                source=self.source,
            )
        ])
        alert = Alert.objects.get(alert_name='Critical Alert')
        created = emit_alarm_notification(alert)
        self.assertEqual(created, 1)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_emit_alarm_notification_skips_when_severity_disabled(self):
        AlarmSetting.objects.filter(severity='Critical').update(is_enabled=False)
        Alert.objects.bulk_create([
            Alert(
                alert_name='Muted Critical Alert',
                severity='Critical',
                rule_level=12,
                alert_time=timezone.now(),
                source=self.source,
            )
        ])
        alert = Alert.objects.get(alert_name='Muted Critical Alert')
        created = emit_alarm_notification(alert)
        self.assertEqual(created, 0)
        self.assertEqual(Notification.objects.count(), 0)


class AlertAggregationTest(TestCase):
    def setUp(self):
        from datetime import timedelta
        from settings_manager.models import AlertAggregationSetting
        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.setting = AlertAggregationSetting.load()
        self.setting.is_enabled = True
        self.setting.window_minutes = 15
        self.setting.group_by_rule = True
        self.setting.group_by_agent = True
        self.setting.group_by_source_ip = True
        self.setting.group_by_destination_ip = False
        self.setting.group_by_username = False
        self.setting.max_events_per_alert = 5
        self.setting.save()

    def test_single_alert_created_when_none_exists(self):
        from alerts.services import ingest_or_aggregate_alert
        data = {
            'alert_name': 'SSH Bruteforce',
            'severity': 'High',
            'rule_id': '5710',
            'agent_id': '001',
            'source_ip': '192.168.1.50',
            'source': self.source,
            'alert_time': timezone.now(),
        }
        alert, created = ingest_or_aggregate_alert(data)
        self.assertTrue(created)
        self.assertEqual(alert.event_count, 1)
        self.assertIsNotNone(alert.aggregation_key)

    def test_alert_aggregated_within_window(self):
        from datetime import timedelta
        from alerts.services import ingest_or_aggregate_alert
        now = timezone.now()
        data = {
            'alert_name': 'SSH Bruteforce',
            'severity': 'High',
            'rule_id': '5710',
            'agent_id': '001',
            'source_ip': '192.168.1.50',
            'source': self.source,
            'alert_time': now,
        }
        alert1, created1 = ingest_or_aggregate_alert(data)
        self.assertTrue(created1)

        # Ingest identical event 2 minutes later
        data2 = data.copy()
        data2['alert_time'] = now + timedelta(minutes=2)
        alert2, created2 = ingest_or_aggregate_alert(data2)
        self.assertFalse(created2)
        self.assertEqual(alert1.id, alert2.id)
        alert2.refresh_from_db()
        self.assertEqual(alert2.event_count, 2)
        self.assertEqual(alert2.last_seen_at, now + timedelta(minutes=2))

    def test_different_ip_creates_separate_alert(self):
        from alerts.services import ingest_or_aggregate_alert
        now = timezone.now()
        data1 = {
            'alert_name': 'SSH Bruteforce',
            'severity': 'High',
            'rule_id': '5710',
            'agent_id': '001',
            'source_ip': '192.168.1.50',
            'source': self.source,
            'alert_time': now,
        }
        alert1, created1 = ingest_or_aggregate_alert(data1)

        data2 = data1.copy()
        data2['source_ip'] = '192.168.1.51'
        alert2, created2 = ingest_or_aggregate_alert(data2)
        self.assertTrue(created2)
        self.assertNotEqual(alert1.id, alert2.id)

    def test_alert_not_aggregated_outside_window(self):
        from datetime import timedelta
        from alerts.services import ingest_or_aggregate_alert
        now = timezone.now()
        data1 = {
            'alert_name': 'SSH Bruteforce',
            'severity': 'High',
            'rule_id': '5710',
            'agent_id': '001',
            'source_ip': '192.168.1.50',
            'source': self.source,
            'alert_time': now - timedelta(minutes=20),
        }
        alert1, created1 = ingest_or_aggregate_alert(data1)

        data2 = data1.copy()
        data2['alert_time'] = now
        alert2, created2 = ingest_or_aggregate_alert(data2)
        self.assertTrue(created2)
        self.assertNotEqual(alert1.id, alert2.id)

    def test_aggregation_disabled_creates_distinct_alerts(self):
        from alerts.services import ingest_or_aggregate_alert
        self.setting.is_enabled = False
        self.setting.save()
        now = timezone.now()
        data = {
            'alert_name': 'SSH Bruteforce',
            'severity': 'High',
            'rule_id': '5710',
            'agent_id': '001',
            'source_ip': '192.168.1.50',
            'source': self.source,
            'alert_time': now,
        }
        alert1, created1 = ingest_or_aggregate_alert(data)
        alert2, created2 = ingest_or_aggregate_alert(data.copy())
        self.assertTrue(created1)
        self.assertTrue(created2)
        self.assertNotEqual(alert1.id, alert2.id)

