from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import (
    Alert, AlertSource, AlertComment, AlertAuditLog, Notification,
    AlertBookmark, SavedFilter,
)
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


class SLABreachAutomationTest(TestCase):
    """Phase 2: periodic SLA-breach worker (detect + notify + auto-escalate)."""

    def setUp(self):
        from datetime import timedelta
        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.manager = User.objects.create_user('socmgr', password='x', email='mgr@example.com')
        profile = self.manager.analyst_profile
        profile.role = 'SOC_MGR'
        profile.is_active = True
        profile.save()
        self.alert = Alert.objects.create(
            alert_name='Old Critical Alert',
            severity='Critical',
            rule_level=12,
            alert_time=timezone.now() - timedelta(hours=48),
            source=self.source,
        )

    def test_breached_alert_is_detected_and_notified(self):
        from django.core.management import call_command
        call_command('check_sla_breaches')
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.sla_status, 'Breached')
        self.assertIsNotNone(self.alert.sla_breach_notified_at)
        self.assertTrue(
            Notification.objects.filter(
                user=self.manager, message__icontains='SLA BREACH'
            ).exists()
        )

    def test_notification_is_idempotent(self):
        from django.core.management import call_command
        call_command('check_sla_breaches')
        first = Notification.objects.filter(message__icontains='SLA BREACH').count()
        call_command('check_sla_breaches')
        second = Notification.objects.filter(message__icontains='SLA BREACH').count()
        self.assertEqual(first, second)
        self.assertGreater(first, 0)

    def test_backfill_suppresses_notification(self):
        from django.core.management import call_command
        call_command('check_sla_breaches', '--backfill')
        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.sla_breach_notified_at)
        self.assertFalse(Notification.objects.filter(message__icontains='SLA BREACH').exists())

    def test_dry_run_writes_nothing(self):
        from django.core.management import call_command
        call_command('check_sla_breaches', '--dry-run')
        self.alert.refresh_from_db()
        self.assertIsNone(self.alert.sla_breach_notified_at)
        self.assertFalse(Notification.objects.filter(message__icontains='SLA BREACH').exists())

    def test_auto_escalate_breached_alert(self):
        from django.core.management import call_command
        call_command('check_sla_breaches', '--auto-escalate')
        self.alert.refresh_from_db()
        self.assertTrue(self.alert.is_escalated)
        self.assertEqual(self.alert.current_tier, 'L2')
        self.assertEqual(self.alert.workflow_state, 'PENDING_L2_ACCEPTANCE')


class EnrichmentStatusTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='TestEnr', source_type='Wazuh')

    def _alert(self, **kwargs):
        defaults = dict(
            alert_name='Enrich Me', severity='High', rule_level=10,
            alert_time=timezone.now(), source=self.source, source_ip='8.8.8.8',
        )
        defaults.update(kwargs)
        return Alert.objects.create(**defaults)

    def test_no_settings_marks_skipped(self):
        from wazuh_integration.enrichment_service import EnrichmentService
        alert = self._alert()
        res = EnrichmentService.enrich_alert(alert)
        self.assertEqual(res['status'], 'Skipped')
        self.assertFalse(res['performed'])
        self.assertEqual(alert.enrichment_status, 'Skipped')

    def test_provider_success_marks_success(self):
        from unittest.mock import patch, MagicMock
        from settings_manager.models import IOCEnrichmentSetting
        from wazuh_integration.enrichment_service import EnrichmentService
        IOCEnrichmentSetting.objects.create(provider_name='IPInfo', is_active=True, auto_enrich=True)
        alert = self._alert()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {'ip': '8.8.8.8', 'city': 'Mountain View', 'country': 'US'}
        with patch('wazuh_integration.enrichment_service.requests.get', return_value=resp):
            res = EnrichmentService.enrich_alert(alert)
        self.assertEqual(res['status'], 'Success')
        self.assertEqual(alert.enrichment_status, 'Success')
        self.assertIn('IPInfo', alert.enrichment_data)
        self.assertIn('IPInfo', alert.enrichment_data['_meta']['providers_ok'])

    def test_partial_when_one_provider_fails(self):
        from unittest.mock import patch, MagicMock
        from settings_manager.models import IOCEnrichmentSetting
        from wazuh_integration.enrichment_service import EnrichmentService
        IOCEnrichmentSetting.objects.create(provider_name='IPInfo', is_active=True, auto_enrich=True)
        IOCEnrichmentSetting.objects.create(provider_name='VirusTotal', api_key='k', is_active=True, auto_enrich=True)
        alert = self._alert(file_hash_sha256='deadbeef')
        ok = MagicMock(status_code=200)
        ok.json.return_value = {'ip': '8.8.8.8', 'country': 'US'}
        bad = MagicMock(status_code=403)
        with patch('wazuh_integration.enrichment_service.requests.get', side_effect=[ok, bad]):
            res = EnrichmentService.enrich_alert(alert)
        self.assertEqual(res['status'], 'Partial')
        self.assertEqual(alert.enrichment_status, 'Partial')
        self.assertIn('VirusTotal', alert.enrichment_data['_meta']['providers_failed'])
        self.assertIn('VirusTotal', alert.enrichment_error)

    def test_failure_marks_failed(self):
        from unittest.mock import patch, MagicMock
        from settings_manager.models import IOCEnrichmentSetting
        from wazuh_integration.enrichment_service import EnrichmentService
        IOCEnrichmentSetting.objects.create(provider_name='IPInfo', is_active=True, auto_enrich=True)
        alert = self._alert()
        bad = MagicMock(status_code=500)
        with patch('wazuh_integration.enrichment_service.requests.get', return_value=bad):
            res = EnrichmentService.enrich_alert(alert)
        self.assertEqual(res['status'], 'Failed')
        self.assertEqual(alert.enrichment_status, 'Failed')

    def test_rerun_endpoint_persists_status(self):
        from unittest.mock import patch, MagicMock
        from django.urls import reverse
        from settings_manager.models import IOCEnrichmentSetting
        user = User.objects.create_superuser('enr_admin', 'e@example.com', 'pw')
        self.client.force_login(user)
        IOCEnrichmentSetting.objects.create(provider_name='IPInfo', is_active=True, auto_enrich=True)
        alert = self._alert()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {'ip': '8.8.8.8', 'country': 'US'}
        url = reverse('alerts:enrich', args=[alert.id])
        with patch('wazuh_integration.enrichment_service.requests.get', return_value=resp):
            r = self.client.post(url)
        self.assertEqual(r.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.enrichment_status, 'Success')


class Phase6SavedFiltersTagsExportTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='P6', source_type='Wazuh')
        self.user = User.objects.create_superuser('p6_admin', 'p6@example.com', 'pw')
        self.client.force_login(self.user)
        self.a1 = Alert.objects.create(
            alert_name='Brute Force Detected', severity='High', rule_level=10,
            alert_time=timezone.now(), source=self.source, tags=['phishing', 'urgent'],
        )
        self.a2 = Alert.objects.create(
            alert_name='Normal Event', severity='Low', rule_level=3,
            alert_time=timezone.now(), source=self.source,
        )

    def test_csv_export(self):
        r = self.client.get(reverse('alerts:export_csv'))
        self.assertEqual(r.status_code, 200)
        self.assertIn('text/csv', r['Content-Type'])
        body = r.content.decode()
        self.assertIn('Brute Force Detected', body)
        self.assertIn('phishing', body)

    def test_csv_export_respects_severity_filter(self):
        r = self.client.get(reverse('alerts:export_csv'), {'severity': 'Low'})
        body = r.content.decode()
        self.assertIn('Normal Event', body)
        self.assertNotIn('Brute Force Detected', body)

    def test_tag_filter(self):
        r = self.client.get(reverse('alerts:table'), {'tag': 'urgent'})
        names = [a.alert_name for a in r.context['alerts']]
        self.assertIn('Brute Force Detected', names)
        self.assertNotIn('Normal Event', names)

    def test_bookmark_toggle(self):
        url = reverse('alerts:bookmark', args=[self.a1.id])
        r = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['is_bookmarked'])
        self.assertTrue(AlertBookmark.objects.filter(user=self.user, alert=self.a1).exists())
        r2 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(r2.json()['is_bookmarked'])
        self.assertFalse(AlertBookmark.objects.filter(user=self.user, alert=self.a1).exists())

    def test_bookmarked_filter(self):
        AlertBookmark.objects.create(user=self.user, alert=self.a1)
        r = self.client.get(reverse('alerts:table'), {'bookmarked': '1'})
        names = [a.alert_name for a in r.context['alerts']]
        self.assertIn('Brute Force Detected', names)
        self.assertNotIn('Normal Event', names)

    def test_set_tags_creates_audit_log(self):
        url = reverse('alerts:set_tags', args=[self.a2.id])
        r = self.client.post(url, {'tags': 'malware, c2 ,malware'})
        self.assertEqual(r.status_code, 302)
        self.a2.refresh_from_db()
        self.assertEqual(self.a2.tags, ['malware', 'c2'])
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.a2, action='Tags Updated').exists())

    def test_saved_filter_save_and_apply(self):
        r = self.client.post(reverse('alerts:saved_filter_save'),
                             {'name': 'High only', 'query': 'severity=High', 'is_shared': '1'})
        self.assertEqual(r.status_code, 302)
        sf = SavedFilter.objects.get(user=self.user, name='High only')
        self.assertTrue(sf.is_shared)
        r2 = self.client.get(reverse('alerts:table'), {'severity': 'High'})
        self.assertContains(r2, 'High only')

    def test_saved_filter_delete_other_user_forbidden(self):
        other = User.objects.create_user('p6_plain', 'p@example.com', 'pw')
        other.analyst_profile.role = 'L1'
        other.analyst_profile.save()
        sf = SavedFilter.objects.create(user=self.user, name='Mine')
        self.client.force_login(other)
        r = self.client.post(reverse('alerts:saved_filter_delete', args=[sf.id]))
        self.assertEqual(r.status_code, 403)

    def test_alert_pdf(self):
        r = self.client.get(reverse('alerts:pdf', args=[self.a1.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))

    def test_detail_shows_bookmark_context(self):
        AlertBookmark.objects.create(user=self.user, alert=self.a1)
        r = self.client.get(reverse('alerts:detail', args=[self.a1.id]))
        self.assertTrue(r.context['is_bookmarked'])


class Phase7AttachmentsWatchersTest(TestCase):
    def setUp(self):
        import tempfile
        from django.test import override_settings
        self._media = tempfile.mkdtemp()
        self._override = override_settings(MEDIA_ROOT=self._media)
        self._override.enable()
        self.addCleanup(self._override.disable)
        self.source = AlertSource.objects.create(name='P7', source_type='Wazuh')
        self.user = User.objects.create_superuser('p7_admin', 'p7@example.com', 'pw')
        self.client.force_login(self.user)
        self.alert = Alert.objects.create(
            alert_name='Evidence Alert', severity='High', rule_level=10,
            alert_time=timezone.now(), source=self.source,
        )

    def _file(self, name='proof.png', content=b'\x89PNG\r\n', content_type='image/png'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(name, content, content_type=content_type)

    def test_attachment_upload_and_download(self):
        from .models import AlertAttachment
        r = self.client.post(
            reverse('alerts:attachment_upload', args=[self.alert.id]),
            {'file': self._file(), 'description': 'screenshot'},
        )
        self.assertEqual(r.status_code, 302)
        att = AlertAttachment.objects.get(alert=self.alert)
        self.assertEqual(att.original_name, 'proof.png')
        self.assertEqual(att.description, 'screenshot')
        self.assertTrue(att.is_image)
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.alert, action='Evidence Attached').exists())
        d = self.client.get(reverse('alerts:attachment_download', args=[att.id]))
        self.assertEqual(d.status_code, 200)

    def test_attachment_rejects_bad_extension(self):
        from .models import AlertAttachment
        r = self.client.post(
            reverse('alerts:attachment_upload', args=[self.alert.id]),
            {'file': self._file('evil.exe', b'MZ')},
        )
        self.assertEqual(r.status_code, 302)
        self.assertFalse(AlertAttachment.objects.filter(alert=self.alert).exists())

    def test_attachment_delete(self):
        from .models import AlertAttachment
        self.client.post(reverse('alerts:attachment_upload', args=[self.alert.id]), {'file': self._file()})
        att = AlertAttachment.objects.get(alert=self.alert)
        r2 = self.client.post(reverse('alerts:attachment_delete', args=[att.id]))
        self.assertEqual(r2.status_code, 302)
        self.assertFalse(AlertAttachment.objects.filter(id=att.id).exists())

    def test_watcher_toggle(self):
        from .models import AlertWatcher
        url = reverse('alerts:watcher_toggle', args=[self.alert.id])
        r = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertTrue(r.json()['is_watching'])
        self.assertTrue(AlertWatcher.objects.filter(alert=self.alert, user=self.user).exists())
        r2 = self.client.post(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertFalse(r2.json()['is_watching'])

    def test_mention_creates_notification_and_watcher(self):
        from .models import AlertWatcher
        bob = User.objects.create_user('p7_bob', 'bob@example.com', 'pw')
        r = self.client.post(
            reverse('alerts:add_comment', args=[self.alert.id]),
            {'comment': 'hey @p7_bob please review'},
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(AlertWatcher.objects.filter(alert=self.alert, user=bob).exists())
        self.assertTrue(Notification.objects.filter(user=bob, message__icontains='mentioned').exists())

    def test_comment_notifies_existing_watcher(self):
        from .models import AlertWatcher
        carol = User.objects.create_user('p7_carol', 'carol@example.com', 'pw')
        AlertWatcher.objects.create(alert=self.alert, user=carol)
        self.client.post(reverse('alerts:add_comment', args=[self.alert.id]), {'comment': 'status update'})
        self.assertTrue(Notification.objects.filter(user=carol, message__icontains='New comment').exists())

    def test_detail_renders_evidence_and_watchers(self):
        r = self.client.get(reverse('alerts:detail', args=[self.alert.id]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachments', r.context)
        self.assertIn('watchers', r.context)


class Phase8RelatedMergeSplitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('p8_admin', 'p8@example.com', 'pw')
        self.client.force_login(self.user)
        self.source = AlertSource.objects.create(name='P8', source_type='Wazuh')
        now = timezone.now()
        self.primary = Alert.objects.create(
            alert_name='Brute force host A', severity='High', rule_level=10,
            alert_time=now, source=self.source,
            source_ip='10.0.0.5', rule_id='5710', agent_id='007', mitre_id='T1110',
        )
        self.same_ip = Alert.objects.create(
            alert_name='Follow-up host A', severity='Medium', rule_level=6,
            alert_time=now, source=self.source,
            source_ip='10.0.0.5', rule_id='5710', agent_id='007',
        )
        self.unrelated = Alert.objects.create(
            alert_name='Unrelated event', severity='Low', rule_level=2,
            alert_time=now, source=self.source,
            source_ip='192.168.1.9', rule_id='9999',
        )

    def test_find_related_alerts(self):
        from .services import find_related_alerts
        ids = [a.id for a in find_related_alerts(self.primary)]
        self.assertIn(self.same_ip.id, ids)
        self.assertNotIn(self.unrelated.id, ids)
        self.assertNotIn(self.primary.id, ids)

    def test_related_json_endpoint(self):
        r = self.client.get(reverse('alerts:related', args=[self.primary.id]))
        self.assertEqual(r.status_code, 200)
        ids = [x['id'] for x in r.json()['related']]
        self.assertIn(self.same_ip.id, ids)
        self.assertNotIn(self.unrelated.id, ids)

    def test_merge_marks_duplicate_and_audits(self):
        r = self.client.post(reverse('alerts:merge', args=[self.primary.id]), {'merge_ids': [self.same_ip.id]})
        self.assertEqual(r.status_code, 302)
        self.same_ip.refresh_from_db()
        self.assertEqual(self.same_ip.merged_into_id, self.primary.id)
        self.assertEqual(self.same_ip.status, 'Closed')
        self.assertEqual(self.same_ip.verdict, 'Duplicate')
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.primary, action='Merged Duplicates').exists())
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.same_ip, action='Merged Into Alert').exists())

    def test_merged_alert_excluded_from_related(self):
        self.same_ip.merged_into = self.primary
        self.same_ip.save(update_fields=['merged_into'])
        from .services import find_related_alerts
        ids = [a.id for a in find_related_alerts(self.primary)]
        self.assertNotIn(self.same_ip.id, ids)

    def test_unmerge_restores_alert(self):
        self.same_ip.merged_into = self.primary
        self.same_ip.status = 'Closed'
        self.same_ip.verdict = 'Duplicate'
        self.same_ip.save(update_fields=['merged_into', 'status', 'verdict'])
        r = self.client.post(reverse('alerts:unmerge', args=[self.same_ip.id]))
        self.assertEqual(r.status_code, 302)
        self.same_ip.refresh_from_db()
        self.assertIsNone(self.same_ip.merged_into_id)
        self.assertEqual(self.same_ip.status, 'New')
        self.assertEqual(self.same_ip.verdict, 'None')
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.same_ip, action='Unmerged From Alert').exists())

    def test_detail_related_and_merged_context(self):
        self.same_ip.merged_into = self.primary
        self.same_ip.save(update_fields=['merged_into'])
        r = self.client.get(reverse('alerts:detail', args=[self.primary.id]))
        self.assertEqual(r.status_code, 200)
        self.assertIn('related_alerts', r.context)
        self.assertEqual(r.context['merged_children'].count(), 1)
        r2 = self.client.get(reverse('alerts:detail', args=[self.same_ip.id]))
        self.assertTrue(r2.context['alert'].is_merged)


class Phase9PlaybooksFalsePositivesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('p9_admin', 'p9@example.com', 'pw')
        self.client.force_login(self.user)
        self.source = AlertSource.objects.create(name='P9', source_type='Wazuh')
        now = timezone.now()
        self.alert = Alert.objects.create(
            alert_name='Suspicious login', severity='High', rule_level=10,
            alert_time=now, source=self.source,
            source_ip='10.0.0.9', rule_id='5710', mitre_tactic='Credential Access',
        )

    def test_playbook_matches_rule(self):
        from settings_manager.models import Playbook
        pb = Playbook.objects.create(
            title='Brute force SOP', match_rule_id='5710', steps='Block IP\nNotify owner',
        )
        self.assertTrue(pb.matches(self.alert))
        self.assertEqual(pb.step_list(), ['Block IP', 'Notify owner'])

    def test_playbook_without_keys_matches_nothing(self):
        from settings_manager.models import Playbook
        pb = Playbook.objects.create(title='Empty', steps='x')
        self.assertFalse(pb.matches(self.alert))
        self.assertEqual(Playbook.for_alert(self.alert), [])

    def test_playbook_ranking_rule_beats_severity(self):
        from settings_manager.models import Playbook
        sev = Playbook.objects.create(title='Broad high', match_severity='High', steps='a')
        rule = Playbook.objects.create(title='Rule specific', match_rule_id='5710', steps='b')
        ordered = Playbook.for_alert(self.alert)
        self.assertEqual(ordered[0], rule)
        self.assertIn(sev, ordered)

    def test_playbook_in_detail_context(self):
        from settings_manager.models import Playbook
        Playbook.objects.create(title='Shown SOP', match_rule_id='5710', steps='step one')
        r = self.client.get(reverse('alerts:detail', args=[self.alert.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([pb.title for pb in r.context['playbooks']], ['Shown SOP'])

    def test_report_fp_creates_record_and_verdict(self):
        from .models import FalsePositiveReport
        r = self.client.post(reverse('alerts:report_fp', args=[self.alert.id]), {'reason': 'known scanner'})
        self.assertEqual(r.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.verdict, 'False Positive')
        rep = FalsePositiveReport.objects.get(alert=self.alert)
        self.assertEqual(rep.rule_id, '5710')
        self.assertEqual(rep.reason, 'known scanner')
        self.assertEqual(rep.reported_by, self.user)
        self.assertTrue(AlertAuditLog.objects.filter(alert=self.alert, action='FP Reported').exists())

    def test_report_fp_requires_verdict_permission(self):
        User.objects.create_user('p9_viewer', 'v@example.com', 'pw')
        viewer = User.objects.get(username='p9_viewer')
        viewer.analyst_profile.role = 'VIEWER'
        viewer.analyst_profile.save()
        self.client.force_login(viewer)
        r = self.client.post(reverse('alerts:report_fp', args=[self.alert.id]), {'reason': 'x'})
        self.assertEqual(r.status_code, 403)

    def test_noisy_rules_page_lists_reported_rule(self):
        from .models import FalsePositiveReport
        FalsePositiveReport.objects.create(alert=self.alert, rule_id='5710', reason='noise', reported_by=self.user)
        r = self.client.get(reverse('settings:noisy_rules'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '5710')

    def test_playbook_form_requires_match_key(self):
        from settings_manager.forms import PlaybookForm
        form = PlaybookForm(data={'title': 'No key', 'steps': 'x', 'priority': 100})
        self.assertFalse(form.is_valid())


class AssignmentAcknowledgesSlaTest(TestCase):
    def setUp(self):
        self.source = AlertSource.objects.create(name='TestAssign', source_type='Wazuh')
        self.user = User.objects.create_superuser('p10_assigner', 'a@example.com', 'pw')
        self.user.analyst_profile.role = 'L2'
        self.user.analyst_profile.save()

    def _make_alert(self, **kwargs):
        defaults = dict(
            alert_name='Assign Alert',
            severity='Critical',
            rule_level=12,
            alert_time=timezone.now(),
            source=self.source,
        )
        defaults.update(kwargs)
        return Alert.objects.create(**defaults)

    def test_assign_to_self_acknowledges_escalated_alert(self):
        alert = self._make_alert(status='Escalated to L2')
        self.assertIsNone(alert.acknowledged_at)
        self.client.force_login(self.user)
        r = self.client.post(reverse('alerts:assign', args=[alert.id]))
        self.assertEqual(r.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.assignee, self.user)
        self.assertIsNotNone(alert.acknowledged_at)
        self.assertEqual(alert.status, 'Escalated to L2')

    def test_assign_preserves_existing_acknowledgement(self):
        from datetime import timedelta
        acked_at = timezone.now() - timedelta(hours=1)
        alert = self._make_alert(status='In Progress', acknowledged_at=acked_at)
        self.client.force_login(self.user)
        self.client.post(reverse('alerts:assign', args=[alert.id]))
        alert.refresh_from_db()
        self.assertEqual(alert.acknowledged_at, acked_at)

    def test_assign_new_alert_sets_in_progress_and_ack(self):
        alert = self._make_alert(status='New', severity='Medium', rule_level=5)
        self.client.force_login(self.user)
        self.client.post(reverse('alerts:assign', args=[alert.id]))
        alert.refresh_from_db()
        self.assertEqual(alert.status, 'In Progress')
        self.assertIsNotNone(alert.acknowledged_at)





