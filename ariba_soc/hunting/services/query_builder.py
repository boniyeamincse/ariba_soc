from .query_validator import (
    TIME_RANGE_PRESETS, ALLOWED_FIELDS, ALLOWED_OPERATORS, BASIC_ONLY_FIELDS,
    L1_MAX_HOURS, L1_MAX_RESULTS, ADVANCED_MAX_DAYS, ADVANCED_MAX_RESULTS,
    QueryValidationError,
)


def build_search_query(filters, is_basic=False):
    size = _validate_and_get_size(filters, is_basic)
    time_filter = _build_time_filter(filters)
    field_filters = _build_field_filters(filters, is_basic)
    must_clauses = _build_must_clauses(filters, is_basic)

    query_body = {
        'size': size,
        'sort': [
            {'timestamp': {'order': 'desc'}},
            {'_id': {'order': 'desc'}},
        ],
        'query': {
            'bool': {
                'filter': time_filter + field_filters,
                'must': must_clauses if must_clauses else [{'match_all': {}}],
            }
        },
    }

    cursor = filters.get('cursor')
    if cursor:
        query_body['search_after'] = cursor.get('sort')

    return query_body


def _validate_and_get_size(filters, is_basic):
    try:
        size = int(filters.get('limit', 100))
    except (TypeError, ValueError):
        size = 100
    max_size = L1_MAX_RESULTS if is_basic else ADVANCED_MAX_RESULTS
    return min(max(1, size), max_size)


def _build_time_filter(filters):
    time_range = filters.get('time_range', '1h')
    if time_range == 'custom':
        start = filters.get('start_time', '')
        end = filters.get('end_time', '')
        if start and end:
            return [{'range': {'timestamp': {'gte': start, 'lte': end}}}]
    if time_range in TIME_RANGE_PRESETS:
        return [{'range': {'timestamp': {'gte': TIME_RANGE_PRESETS[time_range], 'lte': 'now'}}}]
    return [{'range': {'timestamp': {'gte': 'now-1h', 'lte': 'now'}}}]


def _build_field_filters(filters, is_basic):
    field_map = {
        'agent_id': 'agent.id',
        'agent_name': 'agent.name',
        'hostname': 'host.name',
        'rule_id': 'rule.id',
        'rule_level': 'rule.level',
        'srcip': 'srcip',
        'dstip': 'dstip',
        'source_ip': 'source.ip',
        'destination_ip': 'destination.ip',
        'username': 'user.name',
        'decoder': 'decoder.name',
        'location': 'location',
        'mitre_tactic': 'rule.mitre.tactic',
        'mitre_technique': 'rule.mitre.technique',
        'mitre_id': 'rule.mitre.id',
    }

    result = []
    for key, field in field_map.items():
        value = filters.get(key)
        if not value:
            continue
        if is_basic and field not in BASIC_ONLY_FIELDS:
            continue
        result.append({'term': {field: value}})
    return result


def _build_must_clauses(filters, is_basic):
    clauses = []
    query_string = filters.get('query', '').strip()
    if query_string:
        clauses.append({
            'simple_query_string': {
                'query': query_string,
                'fields': ['rule.description', 'full_log', 'data.*'],
                'default_operator': 'and',
            }
        })

    groups = filters.get('groups')
    if groups:
        group_list = [g.strip() for g in groups.split(',') if g.strip()]
        if group_list:
            clauses.append({'terms': {'rule.groups': group_list}})

    return clauses


BASIC_ONLY_FIELDS = frozenset({
    'timestamp', 'agent.id', 'agent.name', 'rule.id', 'rule.level',
    'rule.description', 'srcip', 'dstip', 'user.name',
})
