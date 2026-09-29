import re
import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from alerts.models import Alert, AlertSource, AlertAuditLog
from .models import WazuhSyncLog, WazuhConfiguration, WazuhManagerConfig

logger = logging.getLogger(__name__)


class ManagerClient:
    def __init__(self, config=None):
        if config:
            self.base_url = config.api_url.rstrip('/')
            self.username = config.api_username
            self.password = config.api_password
            self.verify_ssl = config.verify_ssl
            self.timeout = config.timeout
        else:
            self.base_url = settings.WAZUH_API_URL or 'https://10.24.66.2:55000'
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
            logger.error(f'Manager API auth failed: {e}')
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

    def fetch_agents(self):
        try:
            response = self._request('GET', f'{self.base_url}/agents', params={'limit': 500, 'sort': '-id'}, timeout=self.timeout)
            return response.json()
        except Exception as e:
            logger.error(f'Failed to fetch agents: {e}')
            return {'data': {'items': []}}

    def get_manager_status(self):
        try:
            response = self._request('GET', f'{self.base_url}/manager/status', timeout=self.timeout)
            return response.json()
        except Exception as e:
            logger.error(f'Failed to get manager status: {e}')
            return {'error': str(e)}


class IndexerClient:
    def __init__(self, config=None):
        if config is None:
            config = WazuhConfiguration.objects.first()
            if config is None:
                raise ValueError('No WazuhConfiguration found')
        self.base_url = config.api_url.rstrip('/')
        self.username = config.api_username
        self.password = config.api_password
        self.index_pattern = config.es_index_pattern or 'wazuh-alerts-*'
        self.verify_ssl = config.verify_ssl
        self.timeout = config.timeout
        self.session = requests.Session()
        self.session.verify = self.verify_ssl
        self.session.auth = (self.username, self.password)
        adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount('https://', adapter)

    def test_connection(self):
        try:
            response = self.session.get(
                f'{self.base_url}/_cluster/health',
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f'Indexer connection test failed: {e}')
            raise

    def search(self, index_pattern, query_body):
        try:
            response = self.session.post(
                f'{self.base_url}/{index_pattern}/_search',
                json=query_body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f'Indexer search failed: {e}')
            raise

    def fetch_alerts(self, time_range='1h', max_alerts=5000):
        try:
            match = re.fullmatch(r'(\d+)([mhdw])', time_range)
            if match:
                amount, unit = int(match.group(1)), match.group(2)
                delta = {
                    'm': timedelta(minutes=amount),
                    'h': timedelta(hours=amount),
                    'd': timedelta(days=amount),
                    'w': timedelta(weeks=amount),
                }[unit]
                since = (timezone.now() - delta).isoformat()
            else:
                since = time_range

            body = {
                'size': min(max_alerts, 5000),
                'sort': [{'timestamp': {'order': 'desc'}}],
                'query': {
                    'range': {
                        'timestamp': {'gte': since}
                    }
                }
            }
            response = self.session.post(
                f'{self.base_url}/{self.index_pattern}/_search',
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get('hits', {}).get('hits', [])
            items = [h['_source'] for h in hits]
            return {'data': {'items': items}}
        except Exception as e:
            logger.error(f'Failed to fetch alerts from indexer: {e}')
            raise


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


def normalize_es_alert(doc, idx=0):
    timestamp = doc.get('timestamp') or doc.get('@timestamp') or timezone.now()
    rule = doc.get('rule', {})
    agent = doc.get('agent', {})

    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            timestamp = timezone.now()

    mitre_ids = []
    if rule.get('mitre', {}).get('id'):
        mitre_ids = rule['mitre']['id']
    elif doc.get('input', {}).get('mitre', {}).get('id'):
        mitre_ids = doc['input']['mitre']['id']

    return {
        'wazuh_alert_id': doc.get('id') or doc.get('_id') or str(idx),
        'alert_time': timestamp,
        'event_time': doc.get('system_time') or doc.get('timestamp'),
        'alert_name': rule.get('description') or doc.get('rule', {}).get('description') or 'Unknown Alert',
        'description': rule.get('description', ''),
        'rule_description': rule.get('description', ''),
        'severity': map_level_to_severity(rule.get('level', 0)),
        'severity_score': rule.get('level', 0),
        'rule_id': str(rule.get('id', '')),
        'rule_level': rule.get('level', 0),
        'agent_id': str(agent.get('id', '')),
        'agent_name': agent.get('name', ''),
        'agent_ip': agent.get('ip', ''),
        'hostname': agent.get('name', '') or doc.get('agent', {}).get('name', '') or doc.get('host', {}).get('hostname', ''),
        'source_ip': doc.get('srcip') or doc.get('SrcIp') or doc.get('source', {}).get('ip', ''),
        'destination_ip': doc.get('dstip') or doc.get('DstIp') or doc.get('destination', {}).get('ip', ''),
        'username': doc.get('user') or doc.get('dstuser') or doc.get('srcuser', ''),
        'process_name': '',
        'process_user': '',
        'command_line': '',
        'target_file': '',
        'file_path': doc.get('file', {}).get('path', '') if isinstance(doc.get('file'), dict) else '',
        'file_hash_md5': '',
        'file_hash_sha1': '',
        'file_hash_sha256': '',
        'url': '',
        'mitre_id': ', '.join(mitre_ids) if isinstance(mitre_ids, list) else str(mitre_ids),
        'mitre_tactic': '',
        'mitre_technique': '',
        'full_log': doc.get('full_log', ''),
        'location': doc.get('location', ''),
        'decoder_name': doc.get('decoder', {}).get('name', '') if isinstance(doc.get('decoder'), dict) else '',
        'alert_fields': doc,
        'raw_json': doc,
        'source_name': doc.get('agent', {}).get('name', '') or doc.get('data', {}).get('source_name', '') or 'Wazuh',
    }


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


def fetch_wazuh_alerts(time_range='1h', config=None):
    sync_log = WazuhSyncLog.objects.create(status='Running')
    source, _ = AlertSource.objects.get_or_create(name='Wazuh', defaults={'source_type': 'Wazuh'})
    created_count = 0
    fetched_count = 0

    try:
        if config is None:
            config = WazuhConfiguration.objects.first()

        if not config or not config.is_active:
            raise ValueError('Wazuh Indexer configuration is missing or inactive')

        client = IndexerClient(config)

        result = client.fetch_alerts(time_range=time_range)
        alerts_data = result.get('data', {}).get('items', [])
        fetched_count = len(alerts_data)

        existing_ids = set(Alert.objects.filter(
            wazuh_alert_id__in=[str(a.get('id', '')) for a in alerts_data if a.get('id')]
        ).values_list('wazuh_alert_id', flat=True))

        from datetime import timedelta
        from settings_manager.models import AlertAggregationSetting
        agg_setting = AlertAggregationSetting.load()
        cutoff = timezone.now() - timedelta(minutes=agg_setting.window_minutes) if agg_setting.is_enabled else None

        batch = []
        batch_keys = {}
        for i, alert_raw in enumerate(alerts_data):
            alert_id = str(alert_raw.get('id', '')) or str(i)
            if alert_id in existing_ids:
                continue
            try:
                data = normalize_es_alert(alert_raw, i)
                data['source'] = source

                agg_key = agg_setting.generate_aggregation_key(
                    rule_id=str(data.get('rule_id', '')),
                    source_ip=str(data.get('source_ip', '')),
                    destination_ip=str(data.get('destination_ip', '')),
                    agent_id=str(data.get('agent_id', '')),
                    hostname=str(data.get('hostname', '')),
                    username=str(data.get('username', '')),
                ) if agg_setting.is_enabled else ''

                if agg_key:
                    existing_agg = Alert.objects.filter(
                        aggregation_key=agg_key,
                        status__in=['New', 'In Progress', 'Awaiting Action'],
                        last_seen_at__gte=cutoff,
                        event_count__lt=agg_setting.max_events_per_alert,
                    ).order_by('-last_seen_at').first()

                    if existing_agg:
                        existing_agg.event_count += 1
                        existing_agg.last_seen_at = timezone.now()
                        existing_agg.save(update_fields=['event_count', 'last_seen_at', 'updated_at'])
                        continue

                    if agg_key in batch_keys:
                        prev_alert = batch_keys[agg_key]
                        if prev_alert.event_count < agg_setting.max_events_per_alert:
                            prev_alert.event_count += 1
                            prev_alert.last_seen_at = timezone.now()
                            continue

                data['aggregation_key'] = agg_key
                data['event_count'] = 1
                data['first_seen_at'] = timezone.now()
                data['last_seen_at'] = timezone.now()
                alert_obj = Alert(**data)
                batch.append(alert_obj)
                if agg_key:
                    batch_keys[agg_key] = alert_obj
            except Exception as e:
                logger.error(f'Failed to normalize alert {alert_id}: {e}')

        if batch:
            Alert.objects.bulk_create(batch, ignore_conflicts=True, batch_size=100)
            created_count = len(batch)

            # Evaluate escalation rules against each, and enrich.
            from alerts.signals import evaluate_auto_escalation
            from alerts.services import emit_alarm_notification
            from .enrichment_service import EnrichmentService
            new_ids = [a.wazuh_alert_id for a in batch]
            for alert in Alert.objects.filter(wazuh_alert_id__in=new_ids, status='New'):
                evaluate_auto_escalation(alert)
                emit_alarm_notification(alert)
                if EnrichmentService.enrich_alert(alert):
                    alert.save(update_fields=['enrichment_data'])

        sync_log.status = 'Success'
        sync_log.alerts_fetched = fetched_count
        sync_log.alerts_created = created_count
        sync_log.finished_at = timezone.now()
        sync_log.save()

        config.last_sync_at = timezone.now()
        config.save()

    except Exception as e:
        sync_log.status = 'Failed'
        sync_log.error_message = str(e)
        sync_log.finished_at = timezone.now()
        sync_log.save()
        logger.error(f'Wazuh sync failed: {e}')

    return {'fetched': fetched_count, 'created': created_count}
