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
            'query': {
                'bool': {
                    'should': [
                        {'term': {'vulnerability.id': cve_id}},
                        {'term': {'vulnerability.cve': cve_id}},
                    ],
                    'minimum_should_match': 1,
                }
            },
            'sort': [
                {'vulnerability.detected_at': {'order': 'desc', 'unmapped_type': 'date'}},
                {'@timestamp': {'order': 'desc', 'unmapped_type': 'date'}},
            ],
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
            'size': 1000,
            'query': {'term': {'agent.id': str(agent_id).strip()}},
            'sort': [
                {'vulnerability.score.base': {'order': 'desc', 'unmapped_type': 'float'}},
                {'vulnerability.score.cvss.primary.score': {'order': 'desc', 'unmapped_type': 'float'}},
                {'vulnerability.detected_at': {'order': 'desc', 'unmapped_type': 'date'}},
            ],
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
            sev = str(filters['severity']).strip()
            filter_clauses.append({
                'bool': {
                    'should': [
                        {'term': {'vulnerability.severity': sev}},
                        {'term': {'vulnerability.severity': sev.capitalize()}},
                        {'term': {'vulnerability.severity': sev.lower()}},
                        {'term': {'vulnerability.severity': sev.upper()}},
                    ],
                    'minimum_should_match': 1,
                }
            })
        if filters.get('cve_id'):
            cve = str(filters['cve_id']).strip()
            filter_clauses.append({
                'bool': {
                    'should': [
                        {'term': {'vulnerability.id': cve}},
                        {'term': {'vulnerability.cve': cve}},
                        {'wildcard': {'vulnerability.id': f"*{cve}*"}},
                    ],
                    'minimum_should_match': 1,
                }
            })
        if filters.get('agent_id'):
            filter_clauses.append({'term': {'agent.id': str(filters['agent_id']).strip()}})
        if filters.get('status'):
            st = str(filters['status']).strip()
            filter_clauses.append({
                'bool': {
                    'should': [
                        {'term': {'vulnerability.status': st}},
                        {'term': {'vulnerability.status': st.lower()}},
                    ],
                    'minimum_should_match': 1,
                }
            })
        if filters.get('package_name'):
            pkg = str(filters['package_name']).strip()
            filter_clauses.append({
                'bool': {
                    'should': [
                        {'wildcard': {'package.name': f"*{pkg}*"}},
                        {'term': {'package.name': pkg}},
                    ],
                    'minimum_should_match': 1,
                }
            })
        if filters.get('min_cvss'):
            cvss_val = float(filters['min_cvss'])
            filter_clauses.append({
                'bool': {
                    'should': [
                        {'range': {'vulnerability.score.base': {'gte': cvss_val}}},
                        {'range': {'vulnerability.score.cvss.primary.score': {'gte': cvss_val}}},
                    ],
                    'minimum_should_match': 1,
                }
            })
        if filters.get('os'):
            must.append({
                'bool': {
                    'should': [
                        {'match': {'host.os.full': filters['os']}},
                        {'match': {'os.full': filters['os']}},
                    ],
                    'minimum_should_match': 1,
                }
            })

        query = {'bool': {'filter': filter_clauses}}
        if must:
            query['bool']['must'] = must
        else:
            query['bool']['must'] = [{'match_all': {}}]

        return {
            'size': min(max(1, size), 5000),
            'from': from_,
            'query': query,
            'sort': [
                {'vulnerability.score.base': {'order': 'desc', 'unmapped_type': 'float'}},
                {'vulnerability.score.cvss.primary.score': {'order': 'desc', 'unmapped_type': 'float'}},
                {'vulnerability.detected_at': {'order': 'desc', 'unmapped_type': 'date'}},
                {'@timestamp': {'order': 'desc', 'unmapped_type': 'date'}},
            ],
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
        os_info = source.get('host', {}).get('os', {}) or source.get('os', {})

        # Score extraction: Wazuh 4.9 has vulnerability.score.base (float), or legacy vulnerability.score.cvss.primary.score
        score_val = None
        vector_val = ''
        score_obj = vuln.get('score', {})
        if isinstance(score_obj, dict):
            if 'base' in score_obj and score_obj['base'] is not None:
                try:
                    score_val = float(score_obj['base'])
                except (ValueError, TypeError):
                    score_val = None
            elif 'cvss' in score_obj:
                primary = score_obj.get('cvss', {}).get('primary', {})
                score_val = primary.get('score')
                vector_val = primary.get('vector', '')
        elif isinstance(score_obj, (int, float)):
            score_val = float(score_obj)

        # CVE extraction: Wazuh 4.9 has vulnerability.id, legacy has vulnerability.cve
        cve_id = vuln.get('id') or vuln.get('cve') or ''

        # Package version: Wazuh 4.9 has package.version, legacy has package.installed_version
        installed_version = package.get('version') or package.get('installed_version', '')
        vulnerable_version = package.get('fixed_version') or package.get('condition', '')

        # Timestamp: Wazuh 4.9 has vulnerability.detected_at or published_at, fallback to @timestamp
        timestamp = vuln.get('detected_at') or vuln.get('published_at') or source.get('@timestamp', '')

        return {
            'cve_id': cve_id,
            'severity': vuln.get('severity', ''),
            'status': vuln.get('status', ''),
            'description': vuln.get('description', ''),
            'reference': vuln.get('reference', ''),
            'cvss_score': score_val,
            'cvss_vector': vector_val,
            'package_name': package.get('name', ''),
            'installed_version': installed_version,
            'vulnerable_version': vulnerable_version,
            'agent_id': agent.get('id', ''),
            'agent_name': agent.get('name', ''),
            'os': os_info.get('full', ''),
            'timestamp': timestamp,
        }
