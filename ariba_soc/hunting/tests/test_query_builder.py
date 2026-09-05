from django.test import TestCase
from hunting.services.query_builder import build_search_query


class QueryBuilderTests(TestCase):
    def test_empty_filters_default_query(self):
        body = build_search_query({}, is_basic=False)
        self.assertEqual(body['size'], 100)
        self.assertIn('query', body)
        self.assertIn('bool', body['query'])

    def test_query_string_generates_match(self):
        body = build_search_query({'query': 'failed login'}, is_basic=False)
        must = body['query']['bool']['must']
        self.assertTrue(any('simple_query_string' in m for m in must))

    def test_size_limited(self):
        body = build_search_query({'limit': 500}, is_basic=False)
        self.assertEqual(body['size'], 500)

    def test_size_capped_at_100_for_basic(self):
        body = build_search_query({'limit': 500}, is_basic=True)
        self.assertEqual(body['size'], 100)

    def test_agent_id_filter(self):
        body = build_search_query({'agent_id': '001'}, is_basic=False)
        filters = body['query']['bool']['filter']
        self.assertTrue(any('agent.id' in f.get('term', {}) for f in filters))

    def test_source_ip_filter(self):
        body = build_search_query({'source_ip': '10.0.0.1'}, is_basic=False)
        filters = body['query']['bool']['filter']
        self.assertTrue(any('source.ip' in f.get('term', {}) for f in filters))

    def test_time_range_1h(self):
        body = build_search_query({'time_range': '1h'}, is_basic=False)
        filters = body['query']['bool']['filter']
        time_filter = [f for f in filters if 'timestamp' in f.get('range', {})]
        self.assertTrue(len(time_filter) > 0)

    def test_custom_time_range(self):
        body = build_search_query({
            'time_range': 'custom',
            'start_time': '2024-01-01T00:00:00Z',
            'end_time': '2024-01-02T00:00:00Z',
        }, is_basic=False)
        filters = body['query']['bool']['filter']
        time_filter = [f for f in filters if 'timestamp' in f.get('range', {})]
        self.assertTrue(len(time_filter) > 0)

    def test_search_after_cursor(self):
        body = build_search_query({
            'cursor': {'sort': ['2024-01-01', 'abc']},
        }, is_basic=False)
        self.assertEqual(body['search_after'], ['2024-01-01', 'abc'])

    def test_sort_by_timestamp_desc(self):
        body = build_search_query({}, is_basic=False)
        self.assertEqual(body['sort'][0]['timestamp']['order'], 'desc')
