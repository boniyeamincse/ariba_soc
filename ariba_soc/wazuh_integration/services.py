import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from alerts.models import Alert, AlertSource, AlertAuditLog
from .models import WazuhSyncLog, WazuhConfiguration

logger = logging.getLogger(__name__)


class WazuhClient:
    def __init__(self):
        self.base_url = settings.WAZUH_API_URL or 'https://localhost:55000'
        self.username = settings.WAZUH_API_USERNAME or ''
        self.password = settings.WAZUH_API_PASSWORD or ''
        self.verify_ssl = settings.WAZUH_VERIFY_SSL
        self.timeout = settings.WAZUH_API_TIMEOUT
        self.token = None
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount('https://', adapter)

    def authenticate(self):
        try:
            response = self.session.get(
                f'{self.base_url}/security/user/authenticate',
                auth=(self.username, self.password),
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            data = response.json()
            self.token = data.get('data', {}).get('token', '')
            return self.token
        except Exception as e:
            logger.error(f'Wazuh auth failed: {e}')
            raise

    def get_headers(self):
        if not self.token:
            self.authenticate()
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
        }

    def _request(self, method, url, **kwargs):
        for attempt in range(2):
            if not self.token:
                self.authenticate()
            kwargs['headers'] = kwargs.get('headers', {})
            kwargs['headers'].update(self.get_headers())
            response = self.session.request(method, url, **kwargs)
            if response.status_code == 401 and attempt == 0:
                self.token = None
                continue
            response.raise_for_status()
            return response

    def fetch_alerts(self, time_range='1h', max_alerts=5000):
        try:
            all_items = []
            offset = 0
            limit = 500

            if time_range == '1h':
                since = (timezone.now() - timedelta(hours=1)).isoformat()
            elif time_range == '24h':
                since = (timezone.now() - timedelta(hours=24)).isoformat()
            else:
                since = time_range

            while offset < max_alerts:
                params = {
                    'limit': limit,
                    'offset': offset,
                    'sort': '-timestamp',
                    'q': f'timestamp>{since}',
                }
                response = self._request('GET', f'{self.base_url}/alerts', params=params, timeout=self.timeout)
                data = response.json()
                items = data.get('data', {}).get('items', []) or data.get('data', {}).get('affected_items', [])
                if not items:
                    break
                all_items.extend(items)
                offset += limit

            return {'data': {'items': all_items}}
        except Exception as e:
            logger.error(f'Failed to fetch Wazuh alerts: {e}')
            raise

    def fetch_agents(self):
        try:
            response = self._request('GET', f'{self.base_url}/agents', params={'limit': 500, 'sort': '-id'}, timeout=self.timeout)
            return response.json()
        except Exception as e:
            logger.error(f'Failed to fetch agents: {e}')
            return {'data': {'items': []}}


def normalize_alert(wazuh_alert):
    data = wazuh_alert.get('data', wazuh_alert)
    rule = data.get('rule', {})
    agent = data.get('agent', {})
    location = data.get('location', '')

    mitre = {}
    for group in rule.get('groups', []):
        if group.startswith('mitre_'):
            parts = group.split('_', 2)
            if len(parts) >= 3:
                mitre[parts[1]] = parts[2]

    alert_data = {
        'wazuh_alert_id': str(wazuh_alert.get('id', '')),
        'alert_time': datetime.fromtimestamp(wazuh_alert.get('timestamp', 0)) if isinstance(wazuh_alert.get('timestamp'), (int, float)) else timezone.now(),
        'event_time': None,
        'alert_name': rule.get('description', 'Unknown Alert'),
        'description': rule.get('description', ''),
        'rule_description': rule.get('description', ''),
        'severity': map_level_to_severity(rule.get('level', 0)),
        'severity_score': rule.get('level', 0),
        'rule_id': str(rule.get('id', '')),
        'rule_level': rule.get('level', 0),
        'agent_id': str(agent.get('id', '')),
        'agent_name': agent.get('name', ''),
        'agent_ip': agent.get('ip', ''),
        'hostname': agent.get('name', '') or data.get('system_name', ''),
        'source_ip': data.get('srcip', '') or data.get('SrcIp', ''),
        'destination_ip': data.get('dstip', '') or data.get('DstIp', ''),
        'username': data.get('user', '') or data.get('dstuser', '') or data.get('srcuser', ''),
        'process_name': data.get('process', {}).get('name', '') if isinstance(data.get('process'), dict) else '',
        'process_user': '',
        'command_line': '',
        'target_file': '',
        'file_path': '',
        'file_hash_md5': '',
        'file_hash_sha1': '',
        'file_hash_sha256': '',
        'url': '',
        'mitre_id': mitre.get('id', ''),
        'mitre_tactic': mitre.get('tactic', ''),
        'mitre_technique': mitre.get('technique', ''),
        'full_log': data.get('full_log', ''),
        'location': location,
        'decoder_name': data.get('decoder', {}).get('name', '') if isinstance(data.get('decoder'), dict) else '',
        'alert_fields': data,
        'raw_json': wazuh_alert,
        'source_name': 'Wazuh',
    }
    return alert_data


def map_level_to_severity(level):
    if level >= 12:
        return 'Critical'
    elif level >= 8:
        return 'High'
    elif level >= 4:
        return 'Medium'
    elif level >= 1:
        return 'Low'
    return 'Informational'


def fetch_wazuh_alerts(time_range='1h'):
    sync_log = WazuhSyncLog.objects.create(status='Running')
    source, _ = AlertSource.objects.get_or_create(name='Wazuh', defaults={'source_type': 'Wazuh'})
    client = WazuhClient()
    created_count = 0
    fetched_count = 0

    try:
        result = client.fetch_alerts(time_range=time_range)
        alerts_data = result.get('data', {}).get('items', []) if 'data' in result else result.get('data', {}).get('affected_items', [])
        fetched_count = len(alerts_data)

        existing_ids = set(Alert.objects.filter(
            wazuh_alert_id__in=[str(a.get('id', '')) for a in alerts_data if a.get('id')]
        ).values_list('wazuh_alert_id', flat=True))

        batch = []
        for wazuh_alert in alerts_data:
            alert_id = str(wazuh_alert.get('id', ''))
            if not alert_id or alert_id in existing_ids:
                continue
            try:
                data = normalize_alert(wazuh_alert)
                data['source'] = source
                batch.append(Alert(**data))
            except Exception as e:
                logger.error(f'Failed to normalize alert {alert_id}: {e}')

        if batch:
            Alert.objects.bulk_create(batch, ignore_conflicts=True, batch_size=100)
            created_count = len(batch)

        sync_log.status = 'Success'
        sync_log.alerts_fetched = fetched_count
        sync_log.alerts_created = created_count
        sync_log.finished_at = timezone.now()
        sync_log.save()

        config = WazuhConfiguration.objects.first()
        if not config:
            config = WazuhConfiguration.objects.create()
        config.last_sync_at = timezone.now()
        config.save()

    except Exception as e:
        sync_log.status = 'Failed'
        sync_log.error_message = str(e)
        sync_log.finished_at = timezone.now()
        sync_log.save()
        logger.error(f'Wazuh sync failed: {e}')

    return {'fetched': fetched_count, 'created': created_count}
