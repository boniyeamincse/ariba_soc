from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from vulnerabilities.models import VulnerabilityCase, VulnerabilityAuditLog, ALLOWED_TRANSITIONS
from vulnerabilities.services.normalizer import normalize_cve_id, build_vulnerability_key, map_severity_to_priority, sync_vulnerability_from_indexer
from vulnerabilities.services.risk_calculator import calculate_risk_score, calculate_priority, calculate_due_at, is_overdue
from vulnerabilities.services.remediation import (
    assign_case, start_progress, await_patch, await_verification,
    resolve_case, accept_risk, mark_false_positive, reopen_case, add_note,
    RemediationError,
)
from vulnerabilities.services.dashboard_metrics import get_overview_metrics, get_inventory


class VulnerabilityModelTests(TestCase):
    def test_create_vulnerability_case(self):
        case = VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-1234::001::openssl',
            agent_id='001',
            cve_id='CVE-2024-1234',
            package_name='openssl',
            status='NEW',
            priority='HIGH',
        )
        self.assertEqual(case.cve_id, 'CVE-2024-1234')
        self.assertEqual(case.status, 'NEW')

    def test_allowed_transitions(self):
        case = VulnerabilityCase(vulnerability_key='test', agent_id='1', cve_id='CVE-2024-0001', status='NEW')
        self.assertTrue(case.can_transition_to('ASSIGNED'))
        self.assertFalse(case.can_transition_to('RESOLVED'))

    def test_str_representation(self):
        case = VulnerabilityCase(vulnerability_key='CVE-2024-1234::001::openssl', cve_id='CVE-2024-1234')
        self.assertIn('CVE-2024-1234', str(case))


class NormalizerTests(TestCase):
    def test_normalize_cve_id(self):
        self.assertEqual(normalize_cve_id('2024-1234'), 'CVE-2024-1234')
        self.assertEqual(normalize_cve_id('CVE-2024-1234'), 'CVE-2024-1234')
        self.assertEqual(normalize_cve_id(''), '')

    def test_build_vulnerability_key(self):
        key = build_vulnerability_key('CVE-2024-1234', '001', 'openssl')
        self.assertEqual(key, 'CVE-2024-1234::001::openssl')

    def test_map_severity_to_priority(self):
        self.assertEqual(map_severity_to_priority('Critical'), 'CRITICAL')
        self.assertEqual(map_severity_to_priority('High'), 'HIGH')
        self.assertEqual(map_severity_to_priority('Medium', 5.0), 'MEDIUM')
        self.assertEqual(map_severity_to_priority('', 9.5), 'CRITICAL')

    def test_sync_creates_case(self):
        vuln_data = {
            'cve_id': 'CVE-2024-9999',
            'agent_id': '002',
            'package_name': 'nginx',
            'severity': 'High',
            'cvss_score': 7.5,
        }
        case, created = sync_vulnerability_from_indexer(vuln_data)
        self.assertTrue(created)
        self.assertEqual(case.cve_id, 'CVE-2024-9999')
        self.assertEqual(case.priority, 'HIGH')

    def test_sync_update_existing(self):
        VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-8888::003::apache',
            agent_id='003', cve_id='CVE-2024-8888', package_name='apache',
            status='NEW',
        )
        vuln_data = {
            'cve_id': 'CVE-2024-8888',
            'agent_id': '003',
            'package_name': 'apache',
            'severity': 'Critical',
            'cvss_score': 9.8,
        }
        case, created = sync_vulnerability_from_indexer(vuln_data)
        self.assertFalse(created)
        self.assertEqual(case.priority, 'CRITICAL')


class RiskCalculatorTests(TestCase):
    def test_risk_score_basic(self):
        score = calculate_risk_score(7.0)
        self.assertEqual(score, 7.0)

    def test_risk_score_with_critical_asset(self):
        score = calculate_risk_score(7.0, asset_criticality='critical')
        self.assertAlmostEqual(score, 10.0, places=1)

    def test_calculate_priority(self):
        self.assertEqual(calculate_priority(9.5), 'CRITICAL')
        self.assertEqual(calculate_priority(7.0), 'HIGH')
        self.assertEqual(calculate_priority(4.0), 'MEDIUM')
        self.assertEqual(calculate_priority(1.0), 'LOW')
        self.assertEqual(calculate_priority(0.0), 'INFO')

    def test_due_at(self):
        due = calculate_due_at('CRITICAL')
        self.assertIsNotNone(due)
        self.assertTrue(due > timezone.now())


class RemediationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('rem_user', password='testpass123')
        self.owner = User.objects.create_user('rem_owner', password='testpass123')
        self.case = VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-7777::005::test',
            agent_id='005', cve_id='CVE-2024-7777', status='NEW',
        )

    def test_assign(self):
        assign_case(self.case, self.user, self.owner)
        self.assertEqual(self.case.status, 'ASSIGNED')
        self.assertEqual(self.case.owner, self.owner)

    def test_assign_wrong_status(self):
        self.case.status = 'RESOLVED'
        self.case.save()
        with self.assertRaises(RemediationError):
            assign_case(self.case, self.user, self.owner)

    def test_start_progress(self):
        self.case.status = 'ASSIGNED'
        self.case.save()
        start_progress(self.case, self.user)
        self.assertEqual(self.case.status, 'IN_PROGRESS')

    def test_full_remediation_flow(self):
        assign_case(self.case, self.user, self.owner)
        start_progress(self.case, self.owner)
        await_patch(self.case, self.owner)
        await_verification(self.case, self.owner)
        resolve_case(self.case, self.owner)
        self.assertEqual(self.case.status, 'RESOLVED')
        self.assertEqual(self.case.verified_by, self.owner)

    def test_accept_risk(self):
        accept_risk(self.case, self.user, 'Business critical system')
        self.assertTrue(self.case.risk_accepted)
        self.assertEqual(self.case.status, 'RISK_ACCEPTED')

    def test_reopen(self):
        self.case.status = 'RESOLVED'
        self.case.save()
        reopen_case(self.case, self.user, 'Issue recurred')
        self.assertEqual(self.case.status, 'REOPENED')

    def test_false_positive(self):
        mark_false_positive(self.case, self.user)
        self.assertEqual(self.case.status, 'FALSE_POSITIVE')

    def test_add_note(self):
        add_note(self.case, self.user, 'Applied patch 1.2.3')
        self.case.refresh_from_db()
        self.assertEqual(self.case.remediation_note, 'Applied patch 1.2.3')


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('vuln_viewer', password='testpass123')
        self.user.analyst_profile.role = 'L2'
        self.user.analyst_profile.save()
        self.viewer = User.objects.create_user('vuln_readonly', password='testpass123')
        self.viewer.analyst_profile.role = 'VIEWER'
        self.viewer.analyst_profile.save()

    def test_overview_requires_login(self):
        resp = self.client.get('/vulnerabilities/')
        self.assertEqual(resp.status_code, 302)

    def test_overview_accessible(self):
        self.client.login(username='vuln_viewer', password='testpass123')
        resp = self.client.get('/vulnerabilities/')
        self.assertEqual(resp.status_code, 200)

    def test_viewer_gets_403(self):
        self.client.login(username='vuln_readonly', password='testpass123')
        resp = self.client.get('/vulnerabilities/')
        self.assertEqual(resp.status_code, 403)

    def test_inventory_page(self):
        self.client.login(username='vuln_viewer', password='testpass123')
        resp = self.client.get('/vulnerabilities/inventory/')
        self.assertEqual(resp.status_code, 200)

    def test_detail_page(self):
        VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-5555::010::test',
            agent_id='010', cve_id='CVE-2024-5555', status='NEW',
        )
        self.client.login(username='vuln_viewer', password='testpass123')
        resp = self.client.get('/vulnerabilities/CVE-2024-5555::010::test/')
        self.assertEqual(resp.status_code, 200)

    def test_assets_page(self):
        self.client.login(username='vuln_viewer', password='testpass123')
        resp = self.client.get('/vulnerabilities/assets/')
        self.assertEqual(resp.status_code, 200)

    def test_cve_list_page(self):
        self.client.login(username='vuln_viewer', password='testpass123')
        resp = self.client.get('/vulnerabilities/cves/')
        self.assertEqual(resp.status_code, 200)


class DashboardMetricsTests(TestCase):
    def test_overview_metrics_empty(self):
        metrics = get_overview_metrics()
        self.assertEqual(metrics['total'], 0)
        self.assertEqual(metrics['critical_open'], 0)

    def test_overview_metrics_with_data(self):
        VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-1111::001::test',
            agent_id='001', cve_id='CVE-2024-1111', priority='CRITICAL', status='NEW',
        )
        metrics = get_overview_metrics()
        self.assertEqual(metrics['total'], 1)
        self.assertEqual(metrics['critical_open'], 1)

    def test_inventory_empty(self):
        data = get_inventory()
        self.assertEqual(data['total'], 0)

    def test_inventory_with_filter(self):
        VulnerabilityCase.objects.create(
            vulnerability_key='CVE-2024-2222::002::test',
            agent_id='002', cve_id='CVE-2024-2222', status='NEW',
        )
        data = get_inventory({'status': 'NEW'})
        self.assertEqual(data['total'], 1)
        data = get_inventory({'status': 'RESOLVED'})
        self.assertEqual(data['total'], 0)
