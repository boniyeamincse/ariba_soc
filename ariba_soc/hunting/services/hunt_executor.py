import logging
import time as time_module
from django.conf import settings
from .query_builder import build_search_query
from .query_validator import (
    validate_ip, validate_rule_level, validate_time_range, validate_custom_time,
    validate_result_limit, validate_query_string, sanitize_event, encode_cursor,
    decode_cursor, QueryValidationError, SENSITIVE_REDACT_FIELDS,
)

logger = logging.getLogger(__name__)


class HuntExecutor:
    def __init__(self):
        self._indexer = None

    def _get_indexer(self):
        if self._indexer is None:
            from wazuh_integration.services import IndexerClient
            self._indexer = IndexerClient()
        return self._indexer

    def execute_search(self, filters, user):
        from accounts.models import RolePermission
        is_basic = not RolePermission.has_permission(user.analyst_profile.role, 'can_use_advanced_hunting')
        validate_filters(filters, is_basic)
        query_body = build_search_query(filters, is_basic)

        start_time = time_module.time()
        try:
            indexer = self._get_indexer()
            raw_result = indexer.search(
                index_pattern='wazuh-alerts-*',
                query_body=query_body,
            )
        except Exception as e:
            logger.error(f'Indexer search failed: {e}')
            return {
                'success': False,
                'status': 'INDEXER_UNAVAILABLE',
                'message': 'Threat hunting service is temporarily unavailable.',
            }
        elapsed_ms = round((time_module.time() - start_time) * 1000)

        hits = raw_result.get('hits', {}).get('hits', [])
        total = raw_result.get('hits', {}).get('total', {}).get('value', 0)
        if isinstance(total, dict):
            total = total.get('value', 0)

        events = []
        for hit in hits:
            source = hit.get('_source', {})
            events.append(normalize_event(source))

        cursor = None
        if hits:
            last_hit = hits[-1]
            cursor = encode_cursor({'sort': last_hit.get('sort', [])})

        time_range_info = _get_time_range_info(filters)

        _record_audit(user, filters, total, elapsed_ms, True)

        return {
            'success': True,
            'data_source': 'Wazuh Indexer',
            'took_ms': elapsed_ms,
            'total': total,
            'returned': len(events),
            'time_range': time_range_info,
            'next_cursor': cursor,
            'events': events,
        }


def validate_filters(filters, is_basic):
    time_range = filters.get('time_range', '1h')
    validate_time_range(time_range, is_basic)
    if time_range == 'custom':
        validate_custom_time(filters.get('start_time'), filters.get('end_time'))
    validate_result_limit(filters.get('limit', 100), is_basic)
    validate_query_string(filters.get('query', ''))
    validate_ip(filters.get('source_ip'))
    validate_ip(filters.get('destination_ip'))
    validate_ip(filters.get('srcip'))
    validate_ip(filters.get('dstip'))
    validate_rule_level(filters.get('rule_level'))


def normalize_event(source):
    rule = source.get('rule', {})
    agent = source.get('agent', {})
    decoder = source.get('decoder', {})

    mitre_ids = rule.get('mitre', {}).get('id', [])
    if isinstance(mitre_ids, str):
        mitre_ids = [mitre_ids] if mitre_ids else []

    return {
        'timestamp': source.get('timestamp', ''),
        'rule_level': rule.get('level', 0),
        'severity': _map_level(rule.get('level', 0)),
        'rule_id': str(rule.get('id', '')),
        'rule_description': rule.get('description', ''),
        'agent_id': str(agent.get('id', '')),
        'agent_name': agent.get('name', ''),
        'hostname': agent.get('name', ''),
        'source_ip': source.get('srcip', '') or source.get('source', {}).get('ip', ''),
        'destination_ip': source.get('dstip', '') or source.get('destination', {}).get('ip', ''),
        'username': source.get('user', '') or source.get('dstuser', '') or source.get('srcuser', ''),
        'mitre_id': ', '.join(mitre_ids) if isinstance(mitre_ids, list) else str(mitre_ids),
        'mitre_tactic': rule.get('mitre', {}).get('tactic', '') if isinstance(rule.get('mitre'), dict) else '',
        'mitre_technique': rule.get('mitre', {}).get('technique', '') if isinstance(rule.get('mitre'), dict) else '',
        'decoder': decoder.get('name', ''),
        'location': source.get('location', ''),
        'full_log': source.get('full_log', ''),
        'raw_event': sanitize_event(source),
    }


def _map_level(level):
    if level >= 12:
        return 'Critical'
    elif level >= 8:
        return 'High'
    elif level >= 4:
        return 'Medium'
    elif level >= 1:
        return 'Low'
    return 'Informational'


def _get_time_range_info(filters):
    time_range = filters.get('time_range', '1h')
    if time_range == 'custom':
        return {'from': filters.get('start_time', ''), 'to': filters.get('end_time', '')}
    presets = {
        '15m': 'now-15m', '1h': 'now-1h', '6h': 'now-6h',
        '24h': 'now-24h', '7d': 'now-7d', '30d': 'now-30d',
    }
    return {'from': presets.get(time_range, 'now-1h'), 'to': 'now'}


def _record_audit(user, filters, result_count, duration_ms, success):
    safe_filters = {k: v for k, v in filters.items() if k not in ('query',)}
    logger.info(
        f'HUNT_SEARCH user={user.username} role={getattr(user, "analyst_profile", None) and user.analyst_profile.role} '
        f'filters={safe_filters} results={result_count} duration_ms={duration_ms} success={success} '
        f'ip={_get_client_ip(user)}'
    )


def _get_client_ip(user):
    try:
        profile = user.analyst_profile
        return ''
    except Exception:
        return ''
