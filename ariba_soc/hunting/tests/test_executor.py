from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from hunting.services.hunt_executor import HuntExecutor, normalize_event, _map_level
from accounts.models import RolePermission


class NormalizeEventTests(TestCase):
    def test_map_level_critical(self):
        self.assertEqual(_map_level(12), 'Critical')
        self.assertEqual(_map_level(15), 'Critical')

    def test_map_level_high(self):
        self.assertEqual(_map_level(8), 'High')
        self.assertEqual(_map_level(11), 'High')

    def test_map_level_medium(self):
        self.assertEqual(_map_level(4), 'Medium')

    def test_map_level_low(self):
        self.assertEqual(_map_level(1), 'Low')

    def test_map_level_informational(self):
        self.assertEqual(_map_level(0), 'Informational')

    def test_normalize_event_basic(self):
        source = {
            'timestamp': '2024-01-01T00:00:00Z',
            'rule': {'id': '1001', 'level': 10, 'description': 'SSH brute force'},
            'agent': {'id': '001', 'name': 'webserver'},
            'srcip': '192.168.1.100',
        }
        result = normalize_event(source)
        self.assertEqual(result['rule_id'], '1001')
        self.assertEqual(result['rule_level'], 10)
        self.assertEqual(result['severity'], 'High')
        self.assertEqual(result['agent_name'], 'webserver')
        self.assertEqual(result['source_ip'], '192.168.1.100')


class ExecutorTests(TestCase):
    @patch('hunting.services.hunt_executor.HuntExecutor._get_indexer')
    def test_execute_search_success(self, mock_idx):
        user = User.objects.create_user('exec_test', password='testpass123')
        user.analyst_profile.role = 'L2'
        user.analyst_profile.save()
        rp, _ = RolePermission.objects.get_or_create(role='L2')
        rp.can_use_basic_hunting = True
        rp.can_use_advanced_hunting = True
        rp.save()

        mock_client = MagicMock()
        mock_client.search.return_value = {
            'hits': {
                'hits': [
                    {
                        '_source': {
                            'timestamp': '2024-01-01T00:00:00Z',
                            'rule': {'id': '1001', 'level': 8, 'description': 'test'},
                            'agent': {'id': '001', 'name': 'host1'},
                        },
                        'sort': ['2024-01-01T00:00:00Z', '123'],
                    }
                ],
                'total': {'value': 1},
            }
        }
        mock_idx.return_value = mock_client

        executor = HuntExecutor()
        result = executor.execute_search({'query': 'test'}, user)
        self.assertTrue(result['success'])
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['data_source'], 'Wazuh Indexer')

    @patch('hunting.services.hunt_executor.HuntExecutor._get_indexer')
    def test_execute_search_indexer_down(self, mock_idx):
        user = User.objects.create_user('exec_fail', password='testpass123')
        user.analyst_profile.role = 'L2'
        user.analyst_profile.save()
        rp, _ = RolePermission.objects.get_or_create(role='L2')
        rp.can_use_basic_hunting = True
        rp.can_use_advanced_hunting = True
        rp.save()

        mock_client = MagicMock()
        mock_client.search.side_effect = Exception('Connection refused')
        mock_idx.return_value = mock_client

        executor = HuntExecutor()
        result = executor.execute_search({'query': 'test'}, user)
        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'INDEXER_UNAVAILABLE')
