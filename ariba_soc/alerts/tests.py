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

    def test_alert_detail_renders_5w_checklist(self):
        from django.urls import reverse
        user = User.objects.create_superuser('socanalyst', 'soc@example.com', 'password123')
        self.client.force_login(user)

        alert = Alert.objects.create(
            alert_name='SSH Bruteforce Detected',
            severity='High',
            rule_id='5710',
            agent_name='kali-target',
            source_ip='192.168.1.50',
            destination_ip='10.0.0.15',
            username='root',
            source=self.source,
            alert_time=timezone.now(),
        )

        resp = self.client.get(reverse('alerts:detail', args=[alert.id]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SOC Analyst Triage Checklist (5 Ws)')
        self.assertContains(resp, 'WHAT HAPPENED?')
        self.assertContains(resp, 'WHERE DID IT HAPPEN?')
        self.assertContains(resp, 'WHO / WHAT INITIATED?')
        self.assertContains(resp, 'IS IT MALICIOUS?')
        self.assertContains(resp, 'WHAT SHOULD WE DO NEXT?')

    def test_suppression_rule_drop_and_autoclose(self):
        from settings_manager.models import AlertSuppressionRule
        from alerts.services import ingest_or_aggregate_alert

        # 1. Test DROP
        drop_rule = AlertSuppressionRule.objects.create(
            name='Drop Pentest IP',
            source_ip='10.99.99.99',
            action='DROP',
            is_active=True,
        )
        data_drop = {
            'alert_name': 'Portscan',
            'severity': 'Medium',
            'source_ip': '10.99.99.99',
            'source': self.source,
            'alert_time': timezone.now(),
        }
        res_alert, created = ingest_or_aggregate_alert(data_drop)
        self.assertIsNone(res_alert)
        self.assertFalse(created)
        drop_rule.refresh_from_db()
        self.assertEqual(drop_rule.match_count, 1)

        # 2. Test AUTO_CLOSE
        close_rule = AlertSuppressionRule.objects.create(
            name='Auto Close Scheduled Backup',
            rule_id='9999',
            action='AUTO_CLOSE',
            is_active=True,
        )
        data_close = {
            'alert_name': 'Backup Script Execution',
            'severity': 'Low',
            'rule_id': '9999',
            'source': self.source,
            'alert_time': timezone.now(),
        }
        res_alert2, created2 = ingest_or_aggregate_alert(data_close)
        self.assertIsNotNone(res_alert2)
        self.assertTrue(created2)
        self.assertEqual(res_alert2.status, 'Closed')
        self.assertEqual(res_alert2.verdict, 'False Positive')
        self.assertIn('Auto-suppressed by rule', res_alert2.closure_reason)
        close_rule.refresh_from_db()
        self.assertEqual(close_rule.match_count, 1)


class AssetDirectoryAndCriticalityTests(TestCase):
    def setUp(self):
        from .models import Asset, AlertSource
        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.user = User.objects.create_superuser(username='soc_asset_admin', password='password123', email='asset_admin@test.com')
        self.user.analyst_profile.role = 'ADMIN'
        self.user.analyst_profile.save()
        self.client.login(username='soc_asset_admin', password='password123')

        self.dc_asset = Asset.objects.create(
            name='Primary Domain Controller',
            hostname='dc01.corp.local',
            ip_address='10.0.1.10',
            agent_id='001',
            criticality='CRITICAL',
            asset_type='DOMAIN_CONTROLLER',
            environment='PROD',
            business_unit='IT Infrastructure',
        )

        self.test_asset = Asset.objects.create(
            name='Dev Test Machine',
            hostname='test-vm-01',
            ip_address='192.168.1.50',
            criticality='LOW',
            asset_type='WORKSTATION',
            environment='TEST',
        )

    def test_asset_multiplier_defaults(self):
        self.assertEqual(self.dc_asset.criticality_multiplier, 2.0)
        self.assertEqual(self.test_asset.criticality_multiplier, 0.8)

    def test_resolve_asset_for_alert(self):
        from .services import resolve_asset_for_alert
        # Resolve by agent_id
        a1 = resolve_asset_for_alert(agent_id='001')
        self.assertEqual(a1, self.dc_asset)

        # Resolve by hostname
        a2 = resolve_asset_for_alert(hostname='dc01.corp.local')
        self.assertEqual(a2, self.dc_asset)

        # Resolve by destination IP
        a3 = resolve_asset_for_alert(destination_ip='10.0.1.10')
        self.assertEqual(a3, self.dc_asset)

        # Resolve low-criticality asset
        a4 = resolve_asset_for_alert(hostname='test-vm-01')
        self.assertEqual(a4, self.test_asset)

        # Unmatched
        a5 = resolve_asset_for_alert(hostname='unknown-host-xyz')
        self.assertIsNone(a5)

    def test_apply_asset_criticality_multiplier(self):
        from .services import apply_asset_criticality
        # Medium alert on Critical Domain Controller -> Escalates to Critical priority & High severity with 2.0x risk score
        alert = Alert.objects.create(
            alert_name='Suspicious Kerberos Ticket Request',
            severity='Medium',
            severity_score=50,
            priority='Medium',
            hostname='dc01.corp.local',
            agent_id='001',
            source=self.source,
        )
        apply_asset_criticality(alert)
        alert.save()

        self.assertEqual(alert.asset, self.dc_asset)
        self.assertEqual(alert.asset_criticality, 'CRITICAL')
        self.assertEqual(alert.priority, 'Critical')
        self.assertEqual(alert.severity, 'High')
        self.assertTrue(alert.is_incident_candidate)
        # 50 * 2.0 = 100.0
        self.assertEqual(alert.risk_score, 100.0)

    def test_ingest_alert_auto_links_asset(self):
        from .services import ingest_or_aggregate_alert
        data = {
            'alert_name': 'Brute Force Attempt',
            'severity': 'Medium',
            'agent_id': '001',
            'hostname': 'dc01.corp.local',
            'source': self.source,
            'alert_time': timezone.now(),
        }
        alert, created = ingest_or_aggregate_alert(data)
        self.assertTrue(created)
        self.assertEqual(alert.asset, self.dc_asset)
        self.assertEqual(alert.asset_criticality, 'CRITICAL')
        self.assertEqual(alert.priority, 'Critical')
        self.assertEqual(alert.severity, 'High')

    def test_asset_directory_view(self):
        from django.urls import reverse
        resp = self.client.get(reverse('alerts:assets_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'ariba_soc/asset_directory.html')
        self.assertContains(resp, 'SOC Asset Directory')
        self.assertContains(resp, 'dc01.corp.local')
        self.assertContains(resp, 'Mission-Critical')

        # Filter by search
        resp_search = self.client.get(reverse('alerts:assets_list') + '?search=dc01')
        self.assertEqual(resp_search.status_code, 200)
        self.assertContains(resp_search, 'dc01.corp.local')
        self.assertNotContains(resp_search, 'test-vm-01')

    def test_asset_crud_views(self):
        from django.urls import reverse
        from .models import Asset
        # Create
        create_resp = self.client.post(reverse('alerts:asset_create'), {
            'name': 'Core Payment Gateway',
            'hostname': 'paygw01.corp.local',
            'ip_address': '10.0.5.20',
            'criticality': 'CRITICAL',
            'criticality_multiplier': '2.0',
            'asset_type': 'PAYMENT_GATEWAY',
            'environment': 'PROD',
            'business_unit': 'Fintech Core',
            'is_active': 'on',
        })
        self.assertEqual(create_resp.status_code, 302)
        new_asset = Asset.objects.get(hostname='paygw01.corp.local')
        self.assertEqual(new_asset.criticality, 'CRITICAL')

        # Edit GET (JSON for modal)
        edit_get = self.client.get(reverse('alerts:asset_edit', args=[new_asset.id]))
        self.assertEqual(edit_get.status_code, 200)
        self.assertEqual(edit_get.json()['hostname'], 'paygw01.corp.local')

        # Edit POST
        edit_post = self.client.post(reverse('alerts:asset_edit', args=[new_asset.id]), {
            'name': 'Updated Payment Gateway',
            'hostname': 'paygw01.corp.local',
            'ip_address': '10.0.5.20',
            'criticality': 'HIGH',
            'criticality_multiplier': '1.5',
            'asset_type': 'PAYMENT_GATEWAY',
            'environment': 'PROD',
            'business_unit': 'Fintech Core',
            'is_active': 'on',
        })
        self.assertEqual(edit_post.status_code, 302)
        new_asset.refresh_from_db()
        self.assertEqual(new_asset.name, 'Updated Payment Gateway')
        self.assertEqual(new_asset.criticality, 'HIGH')

        # Delete POST
        del_resp = self.client.post(reverse('alerts:asset_delete', args=[new_asset.id]))
        self.assertEqual(del_resp.status_code, 302)
        self.assertFalse(Asset.objects.filter(id=new_asset.id).exists())

    def test_recalculate_all_alerts_risk(self):
        from django.urls import reverse
        from .services import recalculate_alerts_risk_score
        # Create an alert before linking
        Alert.objects.create(
            alert_name='Unlinked Alert on DC',
            severity='Medium',
            hostname='dc01.corp.local',
            source=self.source,
        )
        count = recalculate_alerts_risk_score()
        self.assertGreaterEqual(count, 1)
        linked = Alert.objects.get(alert_name='Unlinked Alert on DC')
        self.assertEqual(linked.asset, self.dc_asset)
        self.assertEqual(linked.priority, 'Critical')




