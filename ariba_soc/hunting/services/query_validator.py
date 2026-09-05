import ipaddress
import re
from django.core.exceptions import ValidationError


ALLOWED_FIELDS = frozenset({
    'timestamp', 'agent.id', 'agent.name', 'host.name',
    'rule.id', 'rule.level', 'rule.description', 'rule.groups',
    'rule.mitre.id', 'rule.mitre.tactic', 'rule.mitre.technique',
    'source.ip', 'destination.ip', 'srcip', 'dstip',
    'user.name', 'decoder.name', 'location', 'full_log',
})

ALLOWED_OPERATORS = frozenset({
    'term', 'terms', 'range', 'match', 'simple_query_string', 'exists',
})

FORBIDDEN_PATTERNS = re.compile(
    r'(script|script_score|runtime_mappings|percolate|regexp|'
    r'stored[_\s]?script|update_by_query|delete_by_query|'
    r'cluster|_update|_delete|_percolate)',
    re.IGNORECASE,
)

SENSITIVE_REDACT_FIELDS = frozenset({
    'password', 'passwd', 'authorization', 'token', 'access_token',
    'refresh_token', 'api_key', 'secret', 'cookie', 'session',
    'private_key', 'credential',
})

L1_MAX_HOURS = 24
L1_MAX_RESULTS = 100
ADVANCED_MAX_DAYS = 30
ADVANCED_MAX_RESULTS = 500
MAX_QUERY_STRING_LENGTH = 2000

TIME_RANGE_PRESETS = {
    '15m': 'now-15m',
    '1h': 'now-1h',
    '6h': 'now-6h',
    '24h': 'now-24h',
    '7d': 'now-7d',
    '30d': 'now-30d',
}

BASIC_ONLY_FIELDS = frozenset({
    'timestamp', 'agent.id', 'agent.name', 'rule.id', 'rule.level',
    'rule.description', 'srcip', 'dstip', 'user.name',
})


class QueryValidationError(Exception):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def validate_ip(value):
    if not value:
        return
    try:
        ipaddress.ip_address(value.strip())
    except ValueError:
        try:
            ipaddress.ip_network(value.strip(), strict=False)
        except ValueError:
            raise QueryValidationError(f'Invalid IP address: {value}')


def validate_rule_level(value):
    if value is None or value == '':
        return
    try:
        level = int(value)
        if not (0 <= level <= 15):
            raise QueryValidationError('Rule level must be between 0 and 15')
    except (TypeError, ValueError):
        raise QueryValidationError(f'Invalid rule level: {value}')


def validate_time_range(time_range, is_basic=False):
    if time_range not in TIME_RANGE_PRESETS and time_range != 'custom':
        raise QueryValidationError(f'Invalid time range: {time_range}')
    if is_basic and time_range in ('30d',):
        raise QueryValidationError('L1 analysts cannot use time ranges exceeding 24 hours')


def validate_custom_time(start, end):
    if not start or not end:
        raise QueryValidationError('Custom time range requires both start and end times')
    try:
        from django.utils.dateparse import parse_datetime
        s = parse_datetime(start)
        e = parse_datetime(end)
        if s is None or e is None:
            raise QueryValidationError('Invalid custom time format')
        if s >= e:
            raise QueryValidationError('Start time must be before end time')
    except QueryValidationError:
        raise
    except Exception:
        raise QueryValidationError('Invalid custom time format')


def validate_result_limit(limit, is_basic=False):
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        raise QueryValidationError('Invalid result limit')
    max_limit = L1_MAX_RESULTS if is_basic else ADVANCED_MAX_RESULTS
    if limit < 1 or limit > max_limit:
        raise QueryValidationError(f'Result limit must be between 1 and {max_limit}')
    return limit


def validate_query_string(query_string):
    if not query_string:
        return
    if len(query_string) > MAX_QUERY_STRING_LENGTH:
        raise QueryValidationError(f'Query string exceeds maximum length of {MAX_QUERY_STRING_LENGTH}')
    if FORBIDDEN_PATTERNS.search(query_string):
        raise QueryValidationError('Query contains forbidden patterns')


def validate_field(field_name, is_basic=False):
    if field_name not in ALLOWED_FIELDS:
        raise QueryValidationError(f'Field not allowed: {field_name}')
    if is_basic and field_name not in BASIC_ONLY_FIELDS:
        raise QueryValidationError(f'Field not available for basic hunting: {field_name}')


def sanitize_event(event_data):
    if not isinstance(event_data, dict):
        return event_data
    sanitized = {}
    for key, value in event_data.items():
        lower_key = key.lower()
        if lower_key in SENSITIVE_REDACT_FIELDS or any(s in lower_key for s in SENSITIVE_REDACT_FIELDS):
            sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_event(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_event(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    return sanitized


def encode_cursor(data):
    import base64
    import json
    try:
        payload = json.dumps(data, default=str)
        return base64.urlsafe_b64encode(payload.encode()).decode()
    except Exception:
        raise QueryValidationError('Failed to encode pagination cursor')


def decode_cursor(cursor):
    import base64
    import json
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(decoded)
        if not isinstance(data, dict):
            raise ValueError
        if 'sort' not in data:
            raise ValueError
        return data
    except Exception:
        raise QueryValidationError('Invalid or tampered pagination cursor')
