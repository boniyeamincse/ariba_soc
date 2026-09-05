import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from accounts.models import AnalystProfile, RolePermission


class HuntingTestBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.l1_user = User.objects.create_user('l1_hunter', password='testpass123')
        self.l1_user.analyst_profile.role = 'L1'
        self.l1_user.analyst_profile.save()

        self.l2_user = User.objects.create_user('l2_hunter', password='testpass123')
        self.l2_user.analyst_profile.role = 'L2'
        self.l2_user.analyst_profile.save()

        self.l3_user = User.objects.create_user('l3_hunter', password='testpass123')
        self.l3_user.analyst_profile.role = 'L3'
        self.l3_user.analyst_profile.save()

        self.viewer_user = User.objects.create_user('viewer_hunter', password='testpass123')
        self.viewer_user.analyst_profile.role = 'VIEWER'
        self.viewer_user.analyst_profile.save()

        self.monitor_user = User.objects.create_user('monitor_hunter', password='testpass123')
        self.monitor_user.analyst_profile.role = 'MONITOR'
        self.monitor_user.analyst_profile.save()

        self.inactive_user = User.objects.create_user('inactive_hunter', password='testpass123')
        self.inactive_user.analyst_profile.is_active = False
        self.inactive_user.analyst_profile.save()

        rp_l1, _ = RolePermission.objects.get_or_create(role='L1')
        rp_l1.can_use_basic_hunting = True
        rp_l1.can_use_advanced_hunting = False
        rp_l1.save()

        rp_l2, _ = RolePermission.objects.get_or_create(role='L2')
        rp_l2.can_use_basic_hunting = True
        rp_l2.can_use_advanced_hunting = True
        rp_l2.save()

        rp_l3, _ = RolePermission.objects.get_or_create(role='L3')
        rp_l3.can_use_basic_hunting = True
        rp_l3.can_use_advanced_hunting = True
        rp_l3.save()

        rp_viewer, _ = RolePermission.objects.get_or_create(role='VIEWER')
        rp_viewer.can_use_basic_hunting = False
        rp_viewer.can_use_advanced_hunting = False
        rp_viewer.save()

        rp_monitor, _ = RolePermission.objects.get_or_create(role='MONITOR')
        rp_monitor.can_use_basic_hunting = False
        rp_monitor.can_use_advanced_hunting = False
        rp_monitor.save()


class HuntingPermissionsTests(HuntingTestBase):
    def test_l1_can_open_live_search(self):
        self.client.login(username='l1_hunter', password='testpass123')
        resp = self.client.get('/hunting/live/')
        self.assertEqual(resp.status_code, 200)

    def test_l2_can_open_live_search(self):
        self.client.login(username='l2_hunter', password='testpass123')
        resp = self.client.get('/hunting/live/')
        self.assertEqual(resp.status_code, 200)

    def test_viewer_receives_403_on_live_search(self):
        self.client.login(username='viewer_hunter', password='testpass123')
        resp = self.client.get('/hunting/live/')
        self.assertEqual(resp.status_code, 403)

    def test_monitor_receives_403_on_live_search(self):
        self.client.login(username='monitor_hunter', password='testpass123')
        resp = self.client.get('/hunting/live/')
        self.assertIn(resp.status_code, [403, 302])

    def test_inactive_profile_receives_403(self):
        self.client.login(username='inactive_hunter', password='testpass123')
        resp = self.client.get('/hunting/live/')
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_request_rejected(self):
        resp = self.client.get('/hunting/live/')
        self.assertEqual(resp.status_code, 302)

    def test_api_returns_json_403(self):
        self.client.login(username='viewer_hunter', password='testpass123')
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'query': 'test'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp['Content-Type'], 'application/json')


class QueryValidatorTests(HuntingTestBase):
    def test_invalid_ip_returns_400(self):
        self.client.login(username='l1_hunter', password='testpass123')
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'source_ip': 'not-an-ip'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_invalid_rule_level_returns_400(self):
        self.client.login(username='l1_hunter', password='testpass123')
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'rule_level': 'abc'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_l1_cannot_request_over_100_results(self):
        self.client.login(username='l1_hunter', password='testpass123')
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'limit': 200}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_l1_cannot_request_30d_time_range(self):
        self.client.login(username='l1_hunter', password='testpass123')
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'time_range': '30d'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_l2_can_request_30d_time_range(self):
        self.client.login(username='l2_hunter', password='testpass123')
        with patch('hunting.services.hunt_executor.HuntExecutor._get_indexer') as mock_idx:
            mock_client = MagicMock()
            mock_client.search.return_value = {'hits': {'hits': [], 'total': {'value': 0}}}
            mock_idx.return_value = mock_client
            resp = self.client.post(
                '/hunting/api/search/',
                data=json.dumps({'time_range': '30d', 'limit': 50}),
                content_type='application/json',
            )
            self.assertEqual(resp.status_code, 200)

    def test_l2_can_request_500_results(self):
        self.client.login(username='l2_hunter', password='testpass123')
        with patch('hunting.services.hunt_executor.HuntExecutor._get_indexer') as mock_idx:
            mock_client = MagicMock()
            mock_client.search.return_value = {'hits': {'hits': [], 'total': {'value': 0}}}
            mock_idx.return_value = mock_client
            resp = self.client.post(
                '/hunting/api/search/',
                data=json.dumps({'limit': 500}),
                content_type='application/json',
            )
            self.assertEqual(resp.status_code, 200)


class IndexerFailureTests(HuntingTestBase):
    def test_indexer_failure_returns_503(self):
        self.client.login(username='l2_hunter', password='testpass123')
        with patch('hunting.services.hunt_executor.HuntExecutor._get_indexer') as mock_idx:
            mock_client = MagicMock()
            mock_client.search.side_effect = Exception('Connection refused')
            mock_idx.return_value = mock_client
            resp = self.client.post(
                '/hunting/api/search/',
                data=json.dumps({'query': 'test'}),
                content_type='application/json',
            )
            self.assertEqual(resp.status_code, 503)
            data = resp.json()
            self.assertFalse(data['success'])
            self.assertEqual(data['status'], 'INDEXER_UNAVAILABLE')


class SensitiveFieldRedactionTests(HuntingTestBase):
    def test_password_field_redacted(self):
        from hunting.services.query_validator import sanitize_event
        event = {
            'password': 'secret123',
            'authorization': 'Bearer abc',
            'token': 'xyz',
            'username': 'admin',
            'rule': {'description': 'test'},
        }
        result = sanitize_event(event)
        self.assertEqual(result['password'], '[REDACTED]')
        self.assertEqual(result['authorization'], '[REDACTED]')
        self.assertEqual(result['token'], '[REDACTED]')
        self.assertEqual(result['username'], 'admin')

    def test_nested_sensitive_fields_redacted(self):
        from hunting.services.query_validator import sanitize_event
        event = {
            'data': {
                'password': 'secret',
                'api_key': 'key123',
                'normal_field': 'value',
            }
        }
        result = sanitize_event(event)
        self.assertEqual(result['data']['password'], '[REDACTED]')
        self.assertEqual(result['data']['api_key'], '[REDACTED]')
        self.assertEqual(result['data']['normal_field'], 'value')


class QueryBuilderTests(HuntingTestBase):
    def test_basic_query_structure(self):
        from hunting.services.query_builder import build_search_query
        filters = {'query': 'failed login', 'time_range': '1h', 'limit': 50}
        body = build_search_query(filters, is_basic=False)
        self.assertEqual(body['size'], 50)
        self.assertIn('query', body)
        self.assertIn('bool', body['query'])
        self.assertIn('filter', body['query']['bool'])
        self.assertIn('must', body['query']['bool'])

    def test_l1_basic_restricted_fields(self):
        from hunting.services.query_builder import build_search_query
        filters = {'time_range': '1h', 'limit': 100}
        body = build_search_query(filters, is_basic=True)
        self.assertEqual(body['size'], 100)

    def test_search_after_cursor(self):
        from hunting.services.query_builder import build_search_query
        filters = {'time_range': '1h', 'limit': 100, 'cursor': {'sort': ['2024-01-01', '123']}}
        body = build_search_query(filters, is_basic=False)
        self.assertEqual(body['search_after'], ['2024-01-01', '123'])


class SearchExecutionTests(HuntingTestBase):
    @patch('hunting.services.hunt_executor.HuntExecutor._get_indexer')
    def test_successful_search(self, mock_idx):
        self.client.login(username='l2_hunter', password='testpass123')
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'timestamp': '2024-01-01T00:00:00Z',
                            'rule': {'id': '1001', 'level': 10, 'description': 'SSH brute force'},
                            'agent': {'id': '001', 'name': 'webserver'},
                            'srcip': '192.168.1.100',
                        },
                        'sort': ['2024-01-01T00:00:00Z', '123'],
                    }
                ],
                'total': {'value': 1},
            }
        }
        mock_idx.return_value = mock_client
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'query': 'SSH'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['returned'], 1)
        self.assertEqual(data['data_source'], 'Wazuh Indexer')
        self.assertIn('events', data)

    @patch('hunting.services.hunt_executor.HuntExecutor._get_indexer')
    def test_pagination_cursor(self, mock_idx):
        self.client.login(username='l2_hunter', password='testpass123')
        mock_client = MagicMock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {'_source': {'timestamp': '2024-01-01T00:00:00Z', 'rule': {}, 'agent': {}}, 'sort': ['ts', '1']}
                ],
                'total': {'value': 1},
            }
        }
        mock_idx.return_value = mock_client
        resp = self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'limit': 1}),
            content_type='application/json',
        )
        data = resp.json()
        self.assertIsNotNone(data['next_cursor'])


class CursorTests(HuntingTestBase):
    def test_tampered_cursor_rejected(self):
        from hunting.services.query_validator import decode_cursor
        with self.assertRaises(Exception):
            decode_cursor('dGFtcGVkX2RhdGE=')

    def test_invalid_base64_cursor_rejected(self):
        from hunting.services.query_validator import decode_cursor
        with self.assertRaises(Exception):
            decode_cursor('!!!invalid!!!')


class AuditTests(HuntingTestBase):
    @patch('hunting.services.hunt_executor.HuntExecutor._get_indexer')
    @patch('hunting.services.hunt_executor.logger')
    def test_search_creates_audit_event(self, mock_logger, mock_idx):
        self.client.login(username='l2_hunter', password='testpass123')
        mock_client = MagicMock()
        mock_client.search.return_value = {'hits': {'hits': [], 'total': {'value': 0}}}
        mock_idx.return_value = mock_client
        self.client.post(
            '/hunting/api/search/',
            data=json.dumps({'query': 'test'}),
            content_type='application/json',
        )
        mock_logger.info.assert_called()
        log_msg = mock_logger.info.call_args[0][0]
        self.assertIn('HUNT_SEARCH', log_msg)


class SafeRenderingTests(HuntingTestBase):
    def test_xss_in_log_content_not_executed(self):
        from hunting.services.query_validator import sanitize_event
        event = {
            'full_log': '<img src=x onerror=alert(1)>',
            'password': 'secret',
            'authorization': 'Bearer abc',
            'token': 'xyz',
            'rule': {'description': 'test'},
        }
        result = sanitize_event(event)
        self.assertNotIn('secret', result['full_log'])
        self.assertEqual(result['password'], '[REDACTED]')
        self.assertEqual(result['authorization'], '[REDACTED]')
        self.assertEqual(result['token'], '[REDACTED]')
