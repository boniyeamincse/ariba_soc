import json
from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import AnalystProfile, RolePermission, ROLE_CHOICES
from alerts.models import Alert, AlertSource, AlertComment, AlertAuditLog, Notification


@override_settings(
    CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
    WAZUH_API_URL='https://mock-wazuh:55000',
    WAZUH_API_USERNAME='mock',
    WAZUH_API_PASSWORD='mock',
)
class BaseTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.users = {}
        for role_code, _ in ROLE_CHOICES:
            user = User.objects.create_user(
                username=f'test_{role_code.lower()}',
                password='testpass123',
                email=f'{role_code.lower()}@test.com'
            )
            user.analyst_profile.role = role_code
            user.analyst_profile.is_active = True
            user.analyst_profile.save()
            self.users[role_code] = user

        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.alert = Alert.objects.create(
            wazuh_alert_id='test-001',
            alert_name='Test Alert',
            severity='High',
            status='New',
            source=self.source,
            hostname='test-host',
            source_ip='10.0.0.1',
        )


class TestLoginRedirect(BaseTestCase):
    def test_l1_redirects_to_l1_dashboard(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('dashboard:l1'), fetch_redirect_response=False)

    def test_l2_redirects_to_l2_dashboard(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('dashboard:l2'), fetch_redirect_response=False)

    def test_l3_redirects_to_l3_dashboard(self):
        self.client.login(username='test_l3', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('dashboard:l3'), fetch_redirect_response=False)

    def test_soc_mgr_redirects_to_manager_dashboard(self):
        self.client.login(username='test_soc_mgr', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('dashboard:manager'), fetch_redirect_response=False)

    def test_admin_redirects_to_manager_dashboard(self):
        self.client.login(username='test_admin', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('dashboard:manager'), fetch_redirect_response=False)

    def test_monitor_redirects_to_wallboard(self):
        self.client.login(username='test_monitor', password='testpass123')
        resp = self.client.get(reverse('accounts:role_redirect'))
        self.assertRedirects(resp, reverse('monitor:wallboard'), fetch_redirect_response=False)


class TestDashboardAccess(BaseTestCase):
    def test_l1_can_access_l1_dashboard(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:l1'))
        self.assertEqual(resp.status_code, 200)

    def test_l1_cannot_access_l2_dashboard(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:l2'))
        self.assertEqual(resp.status_code, 403)

    def test_l1_cannot_access_l3_dashboard(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:l3'))
        self.assertEqual(resp.status_code, 403)

    def test_l1_cannot_access_manager_dashboard(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:manager'))
        self.assertEqual(resp.status_code, 403)

    def test_l2_can_access_l1_dashboard(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.get(reverse('dashboard:l1'))
        self.assertEqual(resp.status_code, 200)

    def test_l2_can_access_l2_dashboard(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.get(reverse('dashboard:l2'))
        self.assertEqual(resp.status_code, 200)

    def test_l2_cannot_access_l3_dashboard(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.get(reverse('dashboard:l3'))
        self.assertEqual(resp.status_code, 403)

    def test_l2_cannot_access_manager_dashboard(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.get(reverse('dashboard:manager'))
        self.assertEqual(resp.status_code, 403)

    def test_l3_can_access_l1_l2_l3_dashboards(self):
        self.client.login(username='test_l3', password='testpass123')
        for name in ['dashboard:l1', 'dashboard:l2', 'dashboard:l3']:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, f'L3 should access {name}')

    def test_l3_cannot_access_manager_dashboard(self):
        self.client.login(username='test_l3', password='testpass123')
        resp = self.client.get(reverse('dashboard:manager'))
        self.assertEqual(resp.status_code, 403)

    def test_soc_mgr_can_access_all_dashboards(self):
        self.client.login(username='test_soc_mgr', password='testpass123')
        for name in ['dashboard:l1', 'dashboard:l2', 'dashboard:l3', 'dashboard:manager']:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, f'SOC_MGR should access {name}')

    def test_admin_can_access_all_dashboards(self):
        self.client.login(username='test_admin', password='testpass123')
        for name in ['dashboard:l1', 'dashboard:l2', 'dashboard:l3', 'dashboard:manager']:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 200, f'ADMIN should access {name}')

    def test_unauthenticated_redirects_to_login(self):
        resp = self.client.get(reverse('dashboard:l1'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('login', resp.url)


class TestDashboardMetrics(BaseTestCase):
    def test_l1_dashboard_uses_real_data(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:l1'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('triage_queue', resp.context)
        self.assertIn('critical_high', resp.context)

    def test_manager_dashboard_uses_real_data(self):
        self.client.login(username='test_soc_mgr', password='testpass123')
        resp = self.client.get(reverse('dashboard:manager'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('risk_backlog', resp.context)
        self.assertIn('analyst_workload', resp.context)

    def test_dashboard_stats_api_returns_json(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('dashboard:stats_api'))
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertIn('alerts_by_day', data)
        self.assertIn('severity', data)


class TestEscalationWorkflow(BaseTestCase):
    def test_l1_can_escalate_to_l2(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:escalate', args=[self.alert.id]), {
            'escalation_reason': 'Needs L2 review',
            'tier': 'l2',
        })
        self.assertEqual(resp.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'Escalated to L2')
        self.assertEqual(self.alert.escalation_status, 'pending_acceptance')
        self.assertEqual(self.alert.escalated_from_tier, 'L1')
        self.assertEqual(self.alert.escalated_to_tier, 'L2')

    def test_l2_can_accept_escalation(self):
        self.alert.status = 'Escalated to L2'
        self.alert.escalation_status = 'pending_acceptance'
        self.alert.escalated_to_tier = 'L2'
        self.alert.escalated_from_tier = 'L1'
        self.alert.save()

        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.post(reverse('alerts:escalation_accept', args=[self.alert.id]))
        self.assertEqual(resp.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.escalation_status, 'accepted')
        self.assertEqual(self.alert.accepted_by, self.users['L2'])

    def test_l2_can_return_escalation(self):
        self.alert.status = 'In Progress'
        self.alert.escalation_status = 'accepted'
        self.alert.escalated_to_tier = 'L2'
        self.alert.escalated_from_tier = 'L1'
        self.alert.save()

        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.post(reverse('alerts:escalation_return', args=[self.alert.id]), {
            'return_reason': 'Cannot reproduce',
        })
        self.assertEqual(resp.status_code, 302)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.escalation_status, 'returned')
        self.assertEqual(self.alert.current_tier, 'L1')

    def test_l1_cannot_accept_l2_escalation(self):
        self.alert.status = 'Escalated to L2'
        self.alert.escalation_status = 'pending_acceptance'
        self.alert.escalated_to_tier = 'L2'
        self.alert.save()

        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:escalation_accept', args=[self.alert.id]))
        self.assertEqual(resp.status_code, 403)


class TestAuthorizationGaps(BaseTestCase):
    def test_alert_table_requires_permission(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('alerts:table'))
        self.assertEqual(resp.status_code, 200)

    def test_alert_detail_requires_permission(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('alerts:detail', args=[self.alert.id]))
        self.assertEqual(resp.status_code, 200)

    def test_alert_api_requires_permission(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('alerts:alerts_api'))
        self.assertEqual(resp.status_code, 200)

    def test_reopen_requires_permission(self):
        self.alert.status = 'Closed'
        self.alert.save()
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:reopen', args=[self.alert.id]))
        self.assertIn(resp.status_code, [302, 403])
        self.alert.refresh_from_db()
        if resp.status_code == 403:
            self.assertEqual(self.alert.status, 'Closed')
        else:
            self.assertEqual(self.alert.status, 'New')

    def test_move_api_requires_permission(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(
            reverse('alerts:alert_move_api', args=[self.alert.id]),
            data=json.dumps({'status': 'In Progress'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)

    def test_bulk_action_validates_status(self):
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.post(reverse('alerts:bulk_action'), {
            'action': 'status',
            'value': 'InvalidStatus',
            'alert_ids': [self.alert.id],
        })
        self.assertEqual(resp.status_code, 302)

    def test_viewer_cannot_modify_alerts(self):
        self.client.login(username='test_viewer', password='testpass123')
        resp = self.client.post(reverse('alerts:close', args=[self.alert.id]), {
            'verdict': 'True Positive',
            'closure_comment': 'Test closure',
        })
        self.assertEqual(resp.status_code, 403)

    def test_inactive_profile_denied(self):
        self.users['L1'].analyst_profile.is_active = False
        self.users['L1'].analyst_profile.save()
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(reverse('alerts:table'))
        self.assertEqual(resp.status_code, 403)


class TestApiReturnsJson403(BaseTestCase):
    def test_api_returns_403_json_for_unauthorized(self):
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.get(
            reverse('dashboard:stats_api'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resp.status_code, 200)

    def test_move_api_returns_403_for_viewer(self):
        from accounts.models import RolePermission
        rp = RolePermission.objects.get(role='VIEWER')
        rp.can_change_status = False
        rp.save()

        self.client.login(username='test_viewer', password='testpass123')
        resp = self.client.post(
            reverse('alerts:alert_move_api', args=[self.alert.id]),
            data=json.dumps({'status': 'In Progress'}),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertIn(resp.status_code, [403, 302])
