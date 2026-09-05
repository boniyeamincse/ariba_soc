import json
from datetime import timedelta
from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from accounts.models import AnalystProfile, RolePermission, ROLE_CHOICES
from alerts.models import (
    Alert, AlertSource, AlertComment, AlertAuditLog, Notification,
    AlertEscalation, AlertTransition,
)
from alerts import workflow


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
                email=f'{role_code.lower()}@test.com',
            )
            user.analyst_profile.role = role_code
            user.analyst_profile.is_active = True
            user.analyst_profile.save()
            self.users[role_code] = user

        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.alert = Alert.objects.create(
            wazuh_alert_id='wf-test-001',
            alert_name='Workflow Test Alert',
            severity='High',
            status='New',
            source=self.source,
            hostname='test-host',
            source_ip='10.0.0.1',
            workflow_state='NEW',
            workflow_version=1,
        )

    def _create_alert(self, **kwargs):
        defaults = {
            'wazuh_alert_id': f'wf-test-{Alert.objects.count() + 1:04d}',
            'alert_name': 'Workflow Test Alert',
            'severity': 'High',
            'status': 'New',
            'source': self.source,
            'hostname': 'test-host',
            'workflow_state': 'NEW',
            'workflow_version': 1,
        }
        defaults.update(kwargs)
        return Alert.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Workflow Service Tests
# ---------------------------------------------------------------------------
class TestWorkflowClaim(BaseTestCase):
    def test_l1_claims_new_alert(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        result = workflow.claim_alert(alert.id, self.users['L1'], 1)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'IN_PROGRESS_L1')
        self.assertEqual(result.assignee, self.users['L1'])
        self.assertEqual(result.current_tier, 'L1')
        self.assertEqual(result.workflow_version, 2)
        self.assertIsNotNone(result.acknowledged_at)
        self.assertEqual(AlertTransition.objects.filter(alert=result, action='claim').count(), 1)

    def test_two_analysts_cannot_claim_same_alert_concurrently(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        workflow.claim_alert(alert.id, self.users['L1'], 1)
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.claim_alert(alert.id, self.users['L2'], 1)
        self.assertIn(ctx.exception.status_code, [409, 400])


class TestWorkflowEscalate(BaseTestCase):
    def test_l1_escalates_to_l2(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1', workflow_version=2)
        result = workflow.escalate_alert(alert.id, self.users['L1'], 'L2', 'Needs review', 2)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'PENDING_L2_ACCEPTANCE')
        self.assertEqual(result.current_tier, 'L2')
        self.assertEqual(result.escalated_from_tier, 'L1')
        self.assertEqual(result.escalated_to_tier, 'L2')
        self.assertTrue(result.is_escalated)
        self.assertEqual(result.workflow_version, 3)
        esc = AlertEscalation.objects.filter(alert=result).first()
        self.assertIsNotNone(esc)
        self.assertEqual(esc.escalation_status, 'PENDING')
        self.assertEqual(esc.source_tier, 'L1')
        self.assertEqual(esc.target_tier, 'L2')

    def test_l1_cannot_escalate_directly_to_l3(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.escalate_alert(alert.id, self.users['L1'], 'L3', 'Skip L2', 1)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_l2_escalates_to_l3(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L2', workflow_version=3)
        alert.current_tier = 'L2'
        alert.escalated_to_tier = 'L2'
        alert.escalation_status = 'accepted'
        alert.save()
        result = workflow.escalate_alert(alert.id, self.users['L2'], 'L3', 'Advanced threat', 3)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'PENDING_L3_ACCEPTANCE')
        self.assertEqual(result.current_tier, 'L3')
        esc = AlertEscalation.objects.filter(alert=result, target_tier='L3').first()
        self.assertIsNotNone(esc)
        self.assertEqual(esc.escalation_status, 'PENDING')


class TestWorkflowAccept(BaseTestCase):
    def test_l2_accepts_pending_escalation(self):
        alert = self._create_alert(
            workflow_state='PENDING_L2_ACCEPTANCE',
            current_tier='L2', escalated_to_tier='L2',
            escalation_status='pending_acceptance', workflow_version=3,
        )
        AlertEscalation.objects.create(
            alert=alert, source_tier='L1', target_tier='L2',
            escalated_by=self.users['L1'], escalation_reason='Review needed',
            escalation_status='PENDING',
        )
        result = workflow.accept_escalation(alert.id, self.users['L2'], 3)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'IN_PROGRESS_L2')
        self.assertEqual(result.assignee, self.users['L2'])
        self.assertEqual(result.escalation_status, 'accepted')
        esc = AlertEscalation.objects.filter(alert=result, target_tier='L2').first()
        self.assertEqual(esc.escalation_status, 'ACCEPTED')
        self.assertEqual(esc.accepted_by, self.users['L2'])
        self.assertIsNotNone(esc.accepted_at)


class TestWorkflowReturn(BaseTestCase):
    def test_l2_returns_escalation_to_l1(self):
        alert = self._create_alert(
            workflow_state='IN_PROGRESS_L2',
            current_tier='L2', escalated_to_tier='L2',
            escalation_status='accepted', workflow_version=4,
        )
        AlertEscalation.objects.create(
            alert=alert, source_tier='L1', target_tier='L2',
            escalated_by=self.users['L1'], escalation_reason='Escalated',
            escalation_status='ACCEPTED', accepted_by=self.users['L2'],
        )
        result = workflow.return_escalation(alert.id, self.users['L2'], 'Cannot reproduce', 4)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'RETURNED_TO_L1')
        self.assertEqual(result.current_tier, 'L1')
        self.assertEqual(result.return_reason, 'Cannot reproduce')
        self.assertEqual(result.returned_by, self.users['L2'])
        esc = AlertEscalation.objects.filter(alert=result, target_tier='L2').first()
        self.assertEqual(esc.escalation_status, 'RETURNED')

    def test_l3_returns_escalation_to_l2(self):
        alert = self._create_alert(
            workflow_state='IN_PROGRESS_L3',
            current_tier='L3', escalated_to_tier='L3',
            escalation_status='accepted', workflow_version=5,
        )
        AlertEscalation.objects.create(
            alert=alert, source_tier='L2', target_tier='L3',
            escalated_by=self.users['L2'], escalation_reason='Advanced analysis',
            escalation_status='ACCEPTED', accepted_by=self.users['L3'],
        )
        result = workflow.return_escalation(alert.id, self.users['L3'], 'Need more data from L2', 5)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'RETURNED_TO_L2')
        self.assertEqual(result.current_tier, 'L2')


class TestWorkflowResolveAndClose(BaseTestCase):
    def test_resolve_alert(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1', workflow_version=2)
        result = workflow.resolve_alert(alert.id, self.users['L1'], 'True Positive', 2)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'RESOLVED')
        self.assertEqual(result.verdict, 'True Positive')
        self.assertIsNotNone(result.resolved_at)

    def test_close_alert(self):
        alert = self._create_alert(workflow_state='RESOLVED', workflow_version=3)
        result = workflow.close_alert(alert.id, self.users['L1'], 'False Positive', 'Tuned out', 3)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'CLOSED')
        self.assertEqual(result.verdict, 'False Positive')
        self.assertIsNotNone(result.closed_at)

    def test_reopen_alert(self):
        alert = self._create_alert(workflow_state='CLOSED', workflow_version=4)
        result = workflow.reopen_alert(alert.id, self.users['L1'], 'New evidence', 4)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'QUEUED_L1')
        self.assertEqual(result.current_tier, 'L1')
        self.assertIsNone(result.assignee)

    def test_create_incident(self):
        alert = self._create_alert(
            workflow_state='IN_PROGRESS_L3',
            current_tier='L3', escalated_to_tier='L3',
            escalation_status='accepted', workflow_version=5,
        )
        result = workflow.create_incident(alert.id, self.users['L3'], 'Confirmed breach', 5)
        result.refresh_from_db()
        self.assertEqual(result.workflow_state, 'INCIDENT')
        self.assertTrue(result.is_incident_candidate)


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------
class TestWorkflowAuthorization(BaseTestCase):
    def test_viewer_gets_403_on_claim(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.claim_alert(alert.id, self.users['VIEWER'], 1)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_monitor_gets_403_on_escalate(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.escalate_alert(alert.id, self.users['MONITOR'], 'L2', 'reason', 1)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_inactive_user_gets_403(self):
        self.users['L1'].analyst_profile.is_active = False
        self.users['L1'].analyst_profile.save()
        alert = self._create_alert(workflow_state='QUEUED_L1')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.claim_alert(alert.id, self.users['L1'], 1)
        self.assertEqual(ctx.exception.status_code, 403)


# ---------------------------------------------------------------------------
# Transition and Audit Tests
# ---------------------------------------------------------------------------
class TestWorkflowTransitions(BaseTestCase):
    def test_claim_creates_transition_and_audit(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        workflow.claim_alert(alert.id, self.users['L1'], 1)
        self.assertEqual(AlertTransition.objects.filter(alert=alert).count(), 1)
        t = AlertTransition.objects.filter(alert=alert).first()
        self.assertEqual(t.from_state, 'QUEUED_L1')
        self.assertEqual(t.to_state, 'IN_PROGRESS_L1')
        self.assertEqual(t.action, 'claim')
        self.assertEqual(t.actor, self.users['L1'])
        self.assertEqual(t.actor_role, 'L1')
        self.assertEqual(AlertAuditLog.objects.filter(alert=alert).count(), 1)

    def test_escalate_creates_transition_and_audit(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1')
        workflow.escalate_alert(alert.id, self.users['L1'], 'L2', 'reason', 1)
        self.assertEqual(AlertTransition.objects.filter(alert=alert).count(), 1)
        self.assertEqual(AlertAuditLog.objects.filter(alert=alert).count(), 1)

    def test_failed_action_does_not_partially_update(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1', workflow_version=1)
        original_version = alert.workflow_version
        with self.assertRaises(workflow.WorkflowError):
            workflow.escalate_alert(alert.id, self.users['L1'], 'L3', 'bad target', 1)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_version, original_version)
        self.assertEqual(alert.workflow_state, 'IN_PROGRESS_L1')
        self.assertEqual(AlertTransition.objects.filter(alert=alert).count(), 0)


# ---------------------------------------------------------------------------
# Invalid Transition Tests
# ---------------------------------------------------------------------------
class TestWorkflowInvalidTransitions(BaseTestCase):
    def test_cannot_claim_already_claimed_alert(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1', workflow_version=2)
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.claim_alert(alert.id, self.users['L1'], 2)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_cannot_escalate_from_queued_state(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.escalate_alert(alert.id, self.users['L1'], 'L2', 'reason', 1)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_cannot_close_new_alert(self):
        alert = self._create_alert(workflow_state='NEW')
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.close_alert(alert.id, self.users['L1'], 'FP', 'reason', 1)
        self.assertEqual(ctx.exception.status_code, 409)


# ---------------------------------------------------------------------------
# Stale Version Tests
# ---------------------------------------------------------------------------
class TestWorkflowStaleVersion(BaseTestCase):
    def test_stale_version_returns_409(self):
        alert = self._create_alert(workflow_state='QUEUED_L1', workflow_version=1)
        workflow.claim_alert(alert.id, self.users['L1'], 1)
        alert.refresh_from_db()
        with self.assertRaises(workflow.WorkflowError) as ctx:
            workflow.claim_alert(alert.id, self.users['L1'], 1)
        self.assertEqual(ctx.exception.status_code, 409)


# ---------------------------------------------------------------------------
# Dashboard Queue Tests
# ---------------------------------------------------------------------------
class TestDashboardQueues(BaseTestCase):
    def test_l1_queue_contains_only_queued_l1(self):
        queued = self._create_alert(workflow_state='QUEUED_L1', wazuh_alert_id='q-001')
        in_progress = self._create_alert(
            workflow_state='IN_PROGRESS_L1', wazuh_alert_id='q-002',
            assignee=self.users['L1'],
        )
        from alerts.models import Alert as AlertModel
        l1_queue = AlertModel.objects.filter(workflow_state='QUEUED_L1')
        self.assertIn(queued, l1_queue)
        self.assertNotIn(in_progress, l1_queue)

    def test_l2_pending_contains_only_pending_l2(self):
        pending = self._create_alert(
            workflow_state='PENDING_L2_ACCEPTANCE', wazuh_alert_id='q-003',
            current_tier='L2', escalated_to_tier='L2',
        )
        not_pending = self._create_alert(
            workflow_state='IN_PROGRESS_L2', wazuh_alert_id='q-004',
            current_tier='L2',
        )
        from alerts.models import Alert as AlertModel
        l2_pending = AlertModel.objects.filter(workflow_state='PENDING_L2_ACCEPTANCE')
        self.assertIn(pending, l2_pending)
        self.assertNotIn(not_pending, l2_pending)

    def test_l3_pending_contains_only_pending_l3(self):
        pending = self._create_alert(
            workflow_state='PENDING_L3_ACCEPTANCE', wazuh_alert_id='q-005',
            current_tier='L3', escalated_to_tier='L3',
        )
        from alerts.models import Alert as AlertModel
        l3_pending = AlertModel.objects.filter(workflow_state='PENDING_L3_ACCEPTANCE')
        self.assertIn(pending, l3_pending)

    def test_incident_candidates_contain_only_incident_state(self):
        incident = self._create_alert(
            workflow_state='INCIDENT', wazuh_alert_id='q-006',
            is_incident_candidate=True,
        )
        not_incident = self._create_alert(
            workflow_state='IN_PROGRESS_L3', wazuh_alert_id='q-007',
            is_incident_candidate=True,
        )
        from alerts.models import Alert as AlertModel
        incidents = AlertModel.objects.filter(workflow_state='INCIDENT')
        self.assertIn(incident, incidents)
        self.assertNotIn(not_incident, incidents)


# ---------------------------------------------------------------------------
# View Integration Tests
# ---------------------------------------------------------------------------
class TestWorkflowViewIntegration(BaseTestCase):
    def test_claim_view(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:claim', args=[alert.id]), {
            'workflow_version': 1,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'IN_PROGRESS_L1')

    def test_escalate_view(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:escalate', args=[alert.id]), {
            'tier': 'L2',
            'escalation_reason': 'Needs L2 review',
            'workflow_version': 1,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'PENDING_L2_ACCEPTANCE')

    def test_accept_view(self):
        alert = self._create_alert(
            workflow_state='PENDING_L2_ACCEPTANCE',
            current_tier='L2', escalated_to_tier='L2',
            escalation_status='pending_acceptance',
        )
        AlertEscalation.objects.create(
            alert=alert, source_tier='L1', target_tier='L2',
            escalated_by=self.users['L1'], escalation_reason='Review',
            escalation_status='PENDING',
        )
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.post(reverse('alerts:escalation_accept', args=[alert.id]), {
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'IN_PROGRESS_L2')

    def test_return_view(self):
        alert = self._create_alert(
            workflow_state='IN_PROGRESS_L2',
            current_tier='L2', escalated_to_tier='L2',
            escalation_status='accepted',
        )
        AlertEscalation.objects.create(
            alert=alert, source_tier='L1', target_tier='L2',
            escalated_by=self.users['L1'], escalation_reason='Review',
            escalation_status='ACCEPTED', accepted_by=self.users['L2'],
        )
        self.client.login(username='test_l2', password='testpass123')
        resp = self.client.post(reverse('alerts:escalation_return', args=[alert.id]), {
            'return_reason': 'Cannot reproduce',
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'RETURNED_TO_L1')

    def test_resolve_view(self):
        alert = self._create_alert(workflow_state='IN_PROGRESS_L1')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:resolve', args=[alert.id]), {
            'resolution': 'False Positive',
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'RESOLVED')

    def test_close_view(self):
        alert = self._create_alert(workflow_state='RESOLVED')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:close', args=[alert.id]), {
            'verdict': 'True Positive',
            'closure_comment': 'Confirmed malicious',
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'CLOSED')

    def test_reopen_view(self):
        alert = self._create_alert(workflow_state='CLOSED')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:reopen', args=[alert.id]), {
            'reopen_reason': 'New evidence',
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'QUEUED_L1')

    def test_create_incident_view(self):
        alert = self._create_alert(
            workflow_state='IN_PROGRESS_L3',
            current_tier='L3', escalated_to_tier='L3',
            escalation_status='accepted',
        )
        self.client.login(username='test_l3', password='testpass123')
        resp = self.client.post(reverse('alerts:create_incident', args=[alert.id]), {
            'incident_reason': 'Confirmed breach',
            'workflow_version': alert.workflow_version,
        })
        self.assertEqual(resp.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.workflow_state, 'INCIDENT')

    def test_unauthenticated_gets_redirect(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        resp = self.client.post(reverse('alerts:claim', args=[alert.id]), {
            'workflow_version': 1,
        })
        self.assertEqual(resp.status_code, 302)

    def test_viewer_gets_403_on_workflow_action(self):
        alert = self._create_alert(workflow_state='QUEUED_L1')
        self.client.login(username='test_viewer', password='testpass123')
        resp = self.client.post(reverse('alerts:claim', args=[alert.id]), {
            'workflow_version': 1,
        })
        self.assertIn(resp.status_code, [403, 302])

    def test_invalid_transition_returns_error(self):
        alert = self._create_alert(workflow_state='NEW')
        self.client.login(username='test_l1', password='testpass123')
        resp = self.client.post(reverse('alerts:escalate', args=[alert.id]), {
            'tier': 'L2',
            'escalation_reason': 'test',
            'workflow_version': 1,
        })
        self.assertIn(resp.status_code, [302, 400])


# ---------------------------------------------------------------------------
# Existing Tests (preserved from original)
# ---------------------------------------------------------------------------
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
        self.assertIn('new_l1_queue', resp.context)
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
