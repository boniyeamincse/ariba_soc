import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from alerts.models import Alert
from incidents.models import Incident, IncidentAlert, IncidentTimeline, IncidentNote
from incidents.workflow import (
    confirm_incident, start_investigation, start_containment,
    mark_eradicated, start_recovery, start_monitoring,
    resolve_incident, close_incident, reopen_incident,
    IncidentWorkflowError, ALLOWED_TRANSITIONS,
)
from incidents.services.incident_creator import (
    create_incident_from_alerts, link_alert_to_incident,
    unlink_alert_from_incident, IncidentCreatorError,
)
from incidents.selectors import get_visible_incidents


class IncidentTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.l2_user = User.objects.create_user('inc_l2', password='testpass123')
        self.l2_user.analyst_profile.role = 'L2'
        self.l2_user.analyst_profile.save()
        self.l3_user = User.objects.create_user('inc_l3', password='testpass123')
        self.l3_user.analyst_profile.role = 'L3'
        self.l3_user.analyst_profile.save()
        self.l1_user = User.objects.create_user('inc_l1', password='testpass123')
        self.l1_user.analyst_profile.role = 'L1'
        self.l1_user.analyst_profile.save()
        self.viewer_user = User.objects.create_user('inc_viewer', password='testpass123')
        self.viewer_user.analyst_profile.role = 'VIEWER'
        self.viewer_user.analyst_profile.save()
        self.monitor_user = User.objects.create_user('inc_monitor', password='testpass123')
        self.monitor_user.analyst_profile.role = 'MONITOR'
        self.monitor_user.analyst_profile.save()
        self.monitor_user.analyst_profile.refresh_from_db()
        self.inactive_user = User.objects.create_user('inc_inactive', password='testpass123')
        self.inactive_user.analyst_profile.is_active = False
        self.inactive_user.analyst_profile.save()

        from accounts.models import RolePermission
        for role in ['L2', 'L3', 'SOC_MGR', 'ADMIN']:
            rp, _ = RolePermission.objects.get_or_create(role=role)
            rp.can_create_incident = True
            rp.can_assign_incident = role in ('L3', 'SOC_MGR', 'ADMIN')
            rp.can_manage_incident = True
            rp.can_close_incident = role in ('L3', 'SOC_MGR', 'ADMIN')
            rp.can_reopen_incident = role in ('L3', 'SOC_MGR', 'ADMIN')
            rp.can_link_incident_alerts = True
            rp.save()

        self.alert1 = Alert.objects.create(
            alert_name='Brute Force SSH', severity='High', status='New',
            agent_id='001', rule_id='1001', rule_level=10,
        )
        self.alert2 = Alert.objects.create(
            alert_name='Malware Detected', severity='Critical', status='New',
            agent_id='002', rule_id='1002', rule_level=15,
        )

    def _create_incident(self, user=None):
        user = user or self.l2_user
        return create_incident_from_alerts(
            alert_ids=[self.alert1.id],
            user=user,
            title='Test Incident',
            description='Test description',
            severity='HIGH',
            priority='HIGH',
            declaration_reason='Testing',
        )


class IncidentModelTests(IncidentTestBase):
    def test_generate_incident_number(self):
        num = Incident.generate_incident_number()
        self.assertIn('INC-', num)

    def test_str_representation(self):
        inc = self._create_incident()
        self.assertIn(inc.incident_number, str(inc))


class CreateIncidentTests(IncidentTestBase):
    def test_l2_creates_incident_from_alert(self):
        inc = self._create_incident()
        self.assertEqual(inc.status, 'NEW')
        self.assertEqual(inc.title, 'Test Incident')
        self.assertIsNotNone(inc.incident_number)

    def test_alert_is_linked(self):
        inc = self._create_incident()
        self.assertEqual(inc.linked_alerts.count(), 1)
        self.assertTrue(inc.linked_alerts.first().is_primary)

    def test_timeline_events_created(self):
        inc = self._create_incident()
        self.assertTrue(inc.timeline.filter(event_type='CREATED').exists())
        self.assertTrue(inc.timeline.filter(event_type='ALERT_LINKED').exists())

    def test_l1_cannot_create_incident(self):
        self.client.login(username='inc_l1', password='testpass123')
        resp = self.client.get('/incidents/create/')
        self.assertEqual(resp.status_code, 403)

    def test_no_alerts_rejected(self):
        with self.assertRaises(IncidentCreatorError):
            create_incident_from_alerts([], self.l2_user, 't', 'd', 'HIGH', 'HIGH', 'r')

    def test_duplicate_alert_rejected(self):
        inc = self._create_incident()
        with self.assertRaises(IncidentCreatorError):
            link_alert_to_incident(inc, self.alert1, self.l2_user)


class LinkAlertTests(IncidentTestBase):
    def test_link_second_alert(self):
        inc = self._create_incident()
        link_alert_to_incident(inc, self.alert2, self.l2_user)
        self.assertEqual(inc.linked_alerts.count(), 2)

    def test_unlink_alert(self):
        inc = self._create_incident()
        link_alert_to_incident(inc, self.alert2, self.l2_user)
        unlink_alert_from_incident(inc, self.alert2, self.l2_user)
        self.assertEqual(inc.linked_alerts.count(), 1)

    def test_unlink_primary_selects_new_primary(self):
        inc = self._create_incident()
        link_alert_to_incident(inc, self.alert2, self.l2_user)
        unlink_alert_from_incident(inc, self.alert1, self.l2_user)
        self.assertTrue(inc.linked_alerts.filter(is_primary=True).exists())

    def test_cannot_unlink_only_alert(self):
        inc = self._create_incident()
        with self.assertRaises(IncidentCreatorError):
            unlink_alert_from_incident(inc, self.alert1, self.l2_user)

    def test_closed_incident_rejects_new_alert(self):
        inc = self._create_incident(self.l3_user)
        confirm_incident(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        resolve_incident(inc, self.l3_user, inc.version, 'Fixed')
        inc.refresh_from_db()
        close_incident(inc, self.l3_user, inc.version, 'Done')
        inc.refresh_from_db()
        with self.assertRaises(IncidentCreatorError):
            link_alert_to_incident(inc, self.alert2, self.l3_user)


class WorkflowTests(IncidentTestBase):
    def test_confirm(self):
        inc = self._create_incident()
        confirm_incident(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'CONFIRMED')

    def test_investigate(self):
        inc = self._create_incident()
        confirm_incident(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'INVESTIGATING')

    def test_contain(self):
        inc = self._create_incident()
        confirm_incident(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        start_containment(inc, self.l2_user, inc.version, evidence='Blocked IP')
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'CONTAINMENT')
        self.assertIsNotNone(inc.contained_at)

    def test_full_lifecycle(self):
        inc = self._create_incident(self.l3_user)
        confirm_incident(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        start_containment(inc, self.l3_user, inc.version, evidence='Contained')
        inc.refresh_from_db()
        mark_eradicated(inc, self.l3_user, inc.version, evidence='Eradicated')
        inc.refresh_from_db()
        start_recovery(inc, self.l3_user, inc.version, evidence='Recovered')
        inc.refresh_from_db()
        start_monitoring(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        resolve_incident(inc, self.l3_user, inc.version, resolution_summary='Resolved')
        inc.refresh_from_db()
        close_incident(inc, self.l3_user, inc.version, closure_reason='Closed')
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'CLOSED')
        self.assertIsNotNone(inc.closed_at)

    def test_invalid_transition_rejected(self):
        inc = self._create_incident()
        with self.assertRaises(IncidentWorkflowError):
            start_investigation(inc, self.l2_user, inc.version)

    def test_stale_version_rejected(self):
        inc = self._create_incident()
        with self.assertRaises(IncidentWorkflowError):
            confirm_incident(inc, self.l2_user, inc.version + 1)

    def test_reopen(self):
        inc = self._create_incident(self.l3_user)
        confirm_incident(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l3_user, inc.version)
        inc.refresh_from_db()
        resolve_incident(inc, self.l3_user, inc.version, 'Resolved')
        inc.refresh_from_db()
        close_incident(inc, self.l3_user, inc.version, 'Closed')
        inc.refresh_from_db()
        reopen_incident(inc, self.l3_user, inc.version, reason='New evidence')
        inc.refresh_from_db()
        self.assertEqual(inc.status, 'REOPENED')

    def test_containment_requires_evidence(self):
        inc = self._create_incident()
        confirm_incident(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        start_investigation(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        with self.assertRaises(IncidentWorkflowError):
            start_containment(inc, self.l2_user, inc.version, evidence='')

    def test_timeline_created_for_each_transition(self):
        inc = self._create_incident()
        confirm_incident(inc, self.l2_user, inc.version)
        inc.refresh_from_db()
        self.assertTrue(inc.timeline.filter(event_type='STATUS_CHANGED').exists())


class ViewTests(IncidentTestBase):
    def test_list_requires_login(self):
        resp = self.client.get('/incidents/')
        self.assertEqual(resp.status_code, 302)

    def test_list_accessible(self):
        self.client.login(username='inc_l2', password='testpass123')
        resp = self.client.get('/incidents/')
        self.assertEqual(resp.status_code, 200)

    def test_monitor_gets_403(self):
        self.client.login(username='inc_monitor', password='testpass123')
        resp = self.client.get('/incidents/')
        self.assertIn(resp.status_code, [403, 302])

    def test_inactive_gets_403(self):
        self.client.login(username='inc_inactive', password='testpass123')
        resp = self.client.get('/incidents/')
        self.assertEqual(resp.status_code, 403)

    def test_detail_page(self):
        inc = self._create_incident()
        self.client.login(username='inc_l2', password='testpass123')
        resp = self.client.get(f'/incidents/{inc.incident_number}/')
        self.assertEqual(resp.status_code, 200)

    def test_create_page(self):
        self.client.login(username='inc_l2', password='testpass123')
        resp = self.client.get(f'/incidents/create/?alerts={self.alert1.id}')
        self.assertEqual(resp.status_code, 200)


class SelectorTests(IncidentTestBase):
    def test_l2_sees_all(self):
        inc = self._create_incident()
        visible = get_visible_incidents(self.l2_user)
        self.assertIn(inc, visible)

    def test_l1_sees_only_linked(self):
        inc = self._create_incident()
        visible = get_visible_incidents(self.l1_user)
        self.assertEqual(visible.count(), 0)

    def test_viewer_sees_none(self):
        visible = get_visible_incidents(self.viewer_user)
        self.assertEqual(visible.count(), 0)

    def test_monitor_sees_none(self):
        visible = get_visible_incidents(self.monitor_user)
        self.assertEqual(visible.count(), 0)
