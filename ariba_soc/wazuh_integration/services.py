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
    
    mitre_ids = rule.get('mitre', {}).get('id', [])
    mitre_tactics = rule.get('mitre', {}).get('tactic', [])
    mitre_techniques = rule.get('mitre', {}).get('technique', [])
    
    pci = rule.get('pci_dss', [])
    gdpr = rule.get('gdpr', [])
    hipaa = rule.get('hipaa', [])
    nist = rule.get('nist_800_53', [])

    return {
        'wazuh_alert_id': doc.get('id', '') or str(index),
        'alert_time': timezone.now(),
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
        'mitre_tactic': ', '.join(mitre_tactics) if isinstance(mitre_tactics, list) else str(mitre_tactics),
        'mitre_technique': ', '.join(mitre_techniques) if isinstance(mitre_techniques, list) else str(mitre_techniques),
        'compliance_pci': ', '.join(pci) if isinstance(pci, list) else str(pci),
        'compliance_gdpr': ', '.join(gdpr) if isinstance(gdpr, list) else str(gdpr),
        'compliance_hipaa': ', '.join(hipaa) if isinstance(hipaa, list) else str(hipaa),
        'compliance_nist': ', '.join(nist) if isinstance(nist, list) else str(nist),
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
        from settings_manager.models import AlertAggregationSetting, AlertSuppressionRule
        agg_setting = AlertAggregationSetting.load()
        cutoff = timezone.now() - timedelta(minutes=agg_setting.window_minutes) if agg_setting.is_enabled else None
        active_suppression_rules = list(AlertSuppressionRule.objects.filter(is_active=True))

        batch = []
        batch_keys = {}
        for i, alert_raw in enumerate(alerts_data):
            alert_id = str(alert_raw.get('id', '')) or str(i)
            if alert_id in existing_ids:
                continue
            try:
                data = normalize_es_alert(alert_raw, i)
                data['source'] = source

                # Evaluate suppression
                matched_srule = None
                for srule in active_suppression_rules:
                    if srule.matches(data):
                        matched_srule = srule
                        srule.match_count += 1
                        srule.save(update_fields=['match_count'])
                        break

                if matched_srule:
                    if matched_srule.action == 'DROP':
                        continue
                    elif matched_srule.action == 'AUTO_CLOSE':
                        data['status'] = 'Closed'
                        data['verdict'] = 'False Positive'
                        data['closure_reason'] = f'Auto-suppressed by rule: {matched_srule.name}'
                        if matched_srule.reason:
                            data['root_cause_summary'] = f'Suppression justification: {matched_srule.reason}'

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
                from alerts.services import apply_asset_criticality
                apply_asset_criticality(alert_obj)
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
