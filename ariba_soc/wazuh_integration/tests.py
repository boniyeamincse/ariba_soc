from django.test import TestCase
from .services import map_level_to_severity


class MapLevelToSeverityTest(TestCase):
    def test_critical(self):
        self.assertEqual(map_level_to_severity(12), 'Critical')
        self.assertEqual(map_level_to_severity(15), 'Critical')

    def test_high(self):
        self.assertEqual(map_level_to_severity(8), 'High')
        self.assertEqual(map_level_to_severity(11), 'High')

    def test_medium(self):
        self.assertEqual(map_level_to_severity(4), 'Medium')
        self.assertEqual(map_level_to_severity(7), 'Medium')

    def test_low(self):
        self.assertEqual(map_level_to_severity(1), 'Low')
        self.assertEqual(map_level_to_severity(3), 'Low')

    def test_informational(self):
        self.assertEqual(map_level_to_severity(0), 'Informational')


class ActiveResponseSOARTest(TestCase):
    def setUp(self):
        from unittest.mock import patch, MagicMock
        from django.contrib.auth.models import User
        from django.urls import reverse
        from alerts.models import Alert, AlertSource, AlertComment, AlertAuditLog
        from .models import ActiveResponseExecution, WazuhManagerConfig
        from .services import ManagerClient

        self.source = AlertSource.objects.create(name='Wazuh', source_type='Wazuh')
        self.alert = Alert.objects.create(
            alert_name='SSH Bruteforce',
            severity='High',
            rule_id='5710',
            source_ip='192.168.1.150',
            agent_id='001',
            agent_name='kali-vm',
            source=self.source,
        )
        self.soc_eng = User.objects.create_user('soceng', 'eng@example.com', 'pass123')
        self.soc_eng.analyst_profile.role = 'SOC_ENG'
        self.soc_eng.analyst_profile.save()

        self.l1_analyst = User.objects.create_user('l1analyst', 'l1@example.com', 'pass123')
        self.l1_analyst.analyst_profile.role = 'L1'
        self.l1_analyst.analyst_profile.save()

    def test_manager_client_execute_active_response_success(self):
        from unittest.mock import patch, MagicMock
        from .services import ManagerClient

        client = ManagerClient()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {'total_affected_items': 1, 'affected_items': ['001'], 'failed_items': []},
            'message': 'Command sent successfully',
            'error': 0
        }
        with patch.object(client.session, 'put', return_value=mock_response), \
             patch.object(client, 'get_headers', return_value={'Authorization': 'Bearer test'}):
            res = client.execute_active_response(command='firewall-drop', agent_id='001', arguments=['-', '192.168.1.150'])
            self.assertTrue(res['success'])
            self.assertIn('successfully', res['message'])

    def test_active_response_execute_view_permission_denied_for_l1(self):
        from django.urls import reverse
        self.client.force_login(self.l1_analyst)
        resp = self.client.post(reverse('wazuh_integration:active_response_execute'), {
            'command': 'firewall-drop',
            'alert_id': self.alert.id,
            'target_ip': '192.168.1.150',
            'agent_id': '001',
        })
        self.assertEqual(resp.status_code, 403)

    def test_active_response_execute_view_success_for_soc_eng(self):
        from unittest.mock import patch
        from django.urls import reverse
        from alerts.models import AlertComment, AlertAuditLog
        from .models import ActiveResponseExecution
        from .services import ManagerClient

        self.client.force_login(self.soc_eng)
        mock_result = {'success': True, 'message': 'Rule applied to agent 001', 'raw': {}}
        with patch.object(ManagerClient, 'execute_active_response', return_value=mock_result):
            resp = self.client.post(
                reverse('wazuh_integration:active_response_execute'),
                {
                    'command': 'firewall-drop',
                    'alert_id': self.alert.id,
                    'target_ip': '192.168.1.150',
                    'agent_id': '001',
                },
                HTTP_X_REQUESTED_WITH='XMLHttpRequest'
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()['status'], 'ok')

            # Verify ActiveResponseExecution record
            execution = ActiveResponseExecution.objects.filter(alert=self.alert).first()
            self.assertIsNotNone(execution)
            self.assertEqual(execution.command, 'firewall-drop')
            self.assertEqual(execution.status, 'SUCCESS')
            self.assertEqual(execution.target_ip, '192.168.1.150')

            # Verify comment and audit log added to Alert
            self.assertTrue(AlertComment.objects.filter(alert=self.alert).exists())
            self.assertTrue(AlertAuditLog.objects.filter(alert=self.alert, action='SOAR Containment').exists())

    def test_active_response_history_view(self):
        from django.urls import reverse
        self.client.force_login(self.soc_eng)
        resp = self.client.get(reverse('wazuh_integration:active_response_history'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'SOAR Active Response Audit Log')

