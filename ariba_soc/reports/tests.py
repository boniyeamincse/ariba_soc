import csv
import io
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from alerts.models import Alert
from accounts.models import AnalystProfile
from settings_manager.models import SLASettings
from reports.services import (
    format_duration_minutes,
    get_sla_targets,
    calculate_mtta_mttr_analytics,
)


class MTTAMTTRServiceTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='analyst_alice', password='password123', first_name='Alice')
        self.user1.analyst_profile.role = 'L1'
        self.user1.analyst_profile.save()

        self.user2 = User.objects.create_user(username='analyst_bob', password='password123', first_name='Bob')
        self.user2.analyst_profile.role = 'L2'
        self.user2.analyst_profile.save()

        self.now = timezone.now()

    def test_format_duration_minutes(self):
        self.assertEqual(format_duration_minutes(None), 'N/A')
        self.assertEqual(format_duration_minutes(0.5), '30s')
        self.assertEqual(format_duration_minutes(14.2), '14m')
        self.assertEqual(format_duration_minutes(120), '2h')
        self.assertEqual(format_duration_minutes(150), '2.5h')
        self.assertEqual(format_duration_minutes(1440), '1d')
        self.assertEqual(format_duration_minutes(2880), '2d')

    def test_get_sla_targets_defaults_and_override(self):
        targets = get_sla_targets()
        self.assertEqual(targets['Critical']['ack_min'], 15)
        self.assertEqual(targets['Critical']['resolve_min'], 240)

        # Create custom SLA setting
        SLASettings.objects.create(
            severity='Critical',
            acknowledge_minutes=10,
            resolve_minutes=120,
            is_active=True
        )
        updated_targets = get_sla_targets()
        self.assertEqual(updated_targets['Critical']['ack_min'], 10)
        self.assertEqual(updated_targets['Critical']['resolve_min'], 120)

    def test_calculate_metrics_empty(self):
        metrics = calculate_mtta_mttr_analytics()
        self.assertEqual(metrics['total_alerts'], 0)
        self.assertIsNone(metrics['avg_mtta_min'])
        self.assertIsNone(metrics['avg_mttr_min'])
        self.assertEqual(metrics['avg_mtta_display'], 'N/A')
        self.assertEqual(metrics['avg_mttr_display'], 'N/A')
        self.assertEqual(metrics['sla_compliance_rate'], 100.0)

    def test_calculate_metrics_with_alerts(self):
        # Alert 1: Critical, acked in 15m, resolved in 90m, within SLA, True Positive
        a1_time = self.now - timedelta(hours=3)
        Alert.objects.create(
            alert_name='Critical Ransomware Activity',
            severity='Critical',
            status='Closed',
            verdict='True Positive',
            alert_time=a1_time,
            acknowledged_at=a1_time + timedelta(minutes=15),
            resolved_at=a1_time + timedelta(minutes=90),
            closed_at=a1_time + timedelta(minutes=90),
            sla_status='Within SLA',
            assignee=self.user1,
        )

        # Alert 2: High, acked in 45m, resolved in 600m (>480m target), breached, False Positive
        a2_time = self.now - timedelta(hours=12)
        Alert.objects.create(
            alert_name='High Suspicious Script',
            severity='High',
            status='Closed',
            verdict='False Positive',
            alert_time=a2_time,
            acknowledged_at=a2_time + timedelta(minutes=45),
            resolved_at=a2_time + timedelta(minutes=600),
            closed_at=a2_time + timedelta(minutes=600),
            sla_status='Breached',
            assignee=self.user2,
        )

        # Alert 3: Medium, unacknowledged, still New
        a3_time = self.now - timedelta(minutes=20)
        Alert.objects.create(
            alert_name='Medium Port Scan',
            severity='Medium',
            status='New',
            verdict='None',
            alert_time=a3_time,
            sla_status='Within SLA',
            assignee=None,
        )

        metrics = calculate_mtta_mttr_analytics()
        self.assertEqual(metrics['total_alerts'], 3)
        self.assertEqual(metrics['total_acknowledged'], 2)
        self.assertEqual(metrics['total_resolved'], 2)

        # MTTA: (15 + 45) / 2 = 30.0 mins
        self.assertAlmostEqual(metrics['avg_mtta_min'], 30.0, places=1)
        self.assertEqual(metrics['avg_mtta_display'], '30m')

        # MTTR: (90 + 600) / 2 = 345.0 mins
        self.assertAlmostEqual(metrics['avg_mttr_min'], 345.0, places=1)

        # SLA Compliance: 2 within SLA, 1 breached -> (2 / 3) * 100 = 66.7%
        self.assertEqual(metrics['total_within_sla'], 2)
        self.assertEqual(metrics['total_breached'], 1)
        self.assertEqual(metrics['sla_compliance_rate'], 66.7)

        # Severity breakdown test
        crit_breakdown = next(item for item in metrics['severity_breakdown'] if item['severity'] == 'Critical')
        self.assertEqual(crit_breakdown['total'], 1)
        self.assertEqual(crit_breakdown['ack_count'], 1)
        self.assertEqual(crit_breakdown['res_count'], 1)
        self.assertEqual(crit_breakdown['breached'], 0)
        self.assertEqual(crit_breakdown['sla_compliance_pct'], 100.0)

        high_breakdown = next(item for item in metrics['severity_breakdown'] if item['severity'] == 'High')
        self.assertEqual(high_breakdown['total'], 1)
        self.assertEqual(high_breakdown['breached'], 1)
        self.assertEqual(high_breakdown['sla_compliance_pct'], 0.0)

        # Analyst breakdown test
        alice_data = next(a for a in metrics['analysts_breakdown'] if a['username'] == 'analyst_alice')
        self.assertEqual(alice_data['assigned'], 1)
        self.assertEqual(alice_data['resolved'], 1)
        self.assertEqual(alice_data['breached'], 0)
        self.assertEqual(alice_data['sla_adherence_pct'], 100.0)
        self.assertEqual(alice_data['tp_rate'], 100.0)

        bob_data = next(a for a in metrics['analysts_breakdown'] if a['username'] == 'analyst_bob')
        self.assertEqual(bob_data['assigned'], 1)
        self.assertEqual(bob_data['resolved'], 1)
        self.assertEqual(bob_data['breached'], 1)
        self.assertEqual(bob_data['sla_adherence_pct'], 0.0)
        self.assertEqual(bob_data['tp_rate'], 0.0)

        # Filtering test: by severity
        crit_only = calculate_mtta_mttr_analytics(severity='Critical')
        self.assertEqual(crit_only['total_alerts'], 1)
        self.assertEqual(crit_only['total_resolved'], 1)

        # Filtering test: by assignee
        alice_only = calculate_mtta_mttr_analytics(assignee_id=self.user1.id)
        self.assertEqual(alice_only['total_alerts'], 1)
        self.assertEqual(alice_only['analysts_breakdown'][0]['username'], 'analyst_alice')

        unassigned_only = calculate_mtta_mttr_analytics(assignee_id='unassigned')
        self.assertEqual(unassigned_only['total_alerts'], 1)


class MTTAMTTRViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='soc_admin', password='password123', email='admin@test.com')
        self.user.analyst_profile.role = 'ADMIN'
        self.user.analyst_profile.save()
        self.client.login(username='soc_admin', password='password123')

        # Create sample alert
        self.alert = Alert.objects.create(
            alert_name='Test Brute Force Attack',
            severity='High',
            status='Closed',
            verdict='True Positive',
            alert_time=timezone.now() - timedelta(hours=1),
            acknowledged_at=timezone.now() - timedelta(minutes=45),
            resolved_at=timezone.now() - timedelta(minutes=10),
            closed_at=timezone.now() - timedelta(minutes=10),
            sla_status='Within SLA',
            assignee=self.user,
        )

    def test_mtta_mttr_analytics_view_anonymous_redirect(self):
        self.client.logout()
        response = self.client.get(reverse('reports:mtta_mttr'))
        self.assertEqual(response.status_code, 302)

    def test_mtta_mttr_analytics_view_authenticated(self):
        response = self.client.get(reverse('reports:mtta_mttr'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'ariba_soc/mtta_mttr_analytics.html')
        self.assertIn('metrics', response.context)
        self.assertEqual(response.context['metrics']['total_alerts'], 1)
        self.assertContains(response, 'MTTA / MTTR & SLA Analytics')
        self.assertContains(response, 'Avg MTTA (Triage)')

    def test_mtta_mttr_analytics_view_filters(self):
        response = self.client.get(reverse('reports:mtta_mttr') + '?range=7d&severity=High')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_range'], '7d')
        self.assertEqual(response.context['selected_severity'], 'High')

    def test_export_mtta_mttr_csv_view(self):
        response = self.client.get(reverse('reports:export_mtta_mttr_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename="ariba_mtta_mttr_sla_analytics.csv"', response['Content-Disposition'])

        content = response.content.decode('utf-8')
        self.assertIn('ARIBA SOC — MTTA / MTTR & SLA PERFORMANCE REPORT', content)
        self.assertIn('Avg MTTA (Mean Time to Acknowledge)', content)
        self.assertIn('--- SEVERITY PERFORMANCE BREAKDOWN ---', content)
        self.assertIn('--- ANALYST PERFORMANCE LEADERBOARD ---', content)
        self.assertIn('soc_admin', content)
