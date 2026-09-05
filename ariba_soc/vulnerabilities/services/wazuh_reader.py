import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class WazuhVulnerabilityReader:
    INDEX_PATTERN = 'wazuh-states-vulnerabilities-*'

    def __init__(self):
        self._indexer = None

    def _get_indexer(self):
        if self._indexer is None:
            from wazuh_integration.services import IndexerClient
            self._indexer = IndexerClient()
        return self._indexer

    def fetch_vulnerabilities(self, filters=None, size=100, from_=0):
        query_body = self._build_query(filters or {}, size, from_)
        try:
            indexer = self._get_indexer()
            result = indexer.search(self.INDEX_PATTERN, query_body)
            return self._normalize_response(result)
        except Exception as e:
            logger.error(f'Failed to fetch vulnerabilities from indexer: {e}')
            return {'success': False, 'status': 'INDEXER_UNAVAILABLE', 'message': 'Vulnerability data is temporarily unavailable.'}

    def fetch_cve_detail(self, cve_id):
        query_body = {
            'size': 100,
            'query': {'term': {'vulnerability.cve': cve_id}},
            'sort': [{'@timestamp': {'order': 'desc'}}],
        }
        try:
            indexer = self._get_indexer()
            result = indexer.search(self.INDEX_PATTERN, query_body)
            return self._normalize_response(result)
        except Exception as e:
            logger.error(f'Failed to fetch CVE detail: {e}')
            return {'success': False, 'status': 'INDEXER_UNAVAILABLE'}

    def fetch_agent_vulnerabilities(self, agent_id):
        query_body = {
            'size': 500,
            'query': {'term': {'agent.id': agent_id}},
            'sort': [{'vulnerability.score.cvss.primary.score': {'order': 'desc'}}],
        }
        try:
            indexer = self._get_indexer()
            result = indexer.search(self.INDEX_PATTERN, query_body)
            return self._normalize_response(result)
        except Exception as e:
            logger.error(f'Failed to fetch agent vulnerabilities: {e}')
            return {'success': False, 'status': 'INDEXER_UNAVAILABLE'}

    def _build_query(self, filters, size, from_):
        must = []
        filter_clauses = []

        if filters.get('severity'):
            filter_clauses.append({'term': {'vulnerability.severity': filters['severity']}})
        if filters.get('cve_id'):
            filter_clauses.append({'term': {'vulnerability.cve': filters['cve_id']}})
        if filters.get('agent_id'):
            filter_clauses.append({'term': {'agent.id': filters['agent_id']}})
        if filters.get('status'):
            filter_clauses.append({'term': {'vulnerability.status': filters['status']}})
        if filters.get('package_name'):
            filter_clauses.append({'wildcard': {'package.name': filters['package_name']}})
        if filters.get('min_cvss'):
            filter_clauses.append({'range': {'vulnerability.score.cvss.primary.score': {'gte': float(filters['min_cvss'])}}})
        if filters.get('os'):
            must.append({'match': {'os.full': filters['os']}})

        query = {'bool': {'filter': filter_clauses}}
        if must:
            query['bool']['must'] = must
        else:
            query['bool']['must'] = [{'match_all': {}}]

        return {
            'size': min(max(1, size), 500),
            'from': from_,
            'query': query,
            'sort': [{'vulnerability.score.cvss.primary.score': {'order': 'desc'}}, {'@timestamp': {'order': 'desc'}}],
        }

    def _normalize_response(self, raw):
        hits = raw.get('hits', {}).get('hits', [])
        total = raw.get('hits', {}).get('total', {})
        if isinstance(total, dict):
            total = total.get('value', 0)

        vulns = []
        for hit in hits:
            source = hit.get('_source', {})
            vulns.append(self._normalize_vulnerability(source))

        return {
            'success': True,
            'total': total,
            'returned': len(vulns),
            'vulnerabilities': vulns,
        }

    def _normalize_vulnerability(self, source):
        vuln = source.get('vulnerability', {})
        agent = source.get('agent', {})
        package = source.get('package', {})
        os_info = source.get('os', {})
        score = vuln.get('score', {}).get('cvss', {}).get('primary', {})

        return {
            'cve_id': vuln.get('cve', ''),
            'severity': vuln.get('severity', ''),
            'status': vuln.get('status', ''),
            'description': vuln.get('description', ''),
            'reference': vuln.get('reference', ''),
            'cvss_score': score.get('score', None),
            'cvss_vector': score.get('vector', ''),
            'package_name': package.get('name', ''),
            'installed_version': package.get('installed_version', ''),
            'vulnerable_version': package.get('fixed_version', ''),
            'agent_id': agent.get('id', ''),
            'agent_name': agent.get('name', ''),
            'os': os_info.get('full', ''),
            'timestamp': source.get('@timestamp', ''),
        }
