import requests
from django.utils import timezone
from django.core.cache import cache
from settings_manager.models import IOCEnrichmentSetting
import logging

logger = logging.getLogger(__name__)

class EnrichmentService:
    @staticmethod
    def enrich_alert(alert):
        """
        Enriches an alert if there are active IOCEnrichmentSettings and auto_enrich is enabled.

        Records status on the alert (enrichment_status / enrichment_updated_at /
        enrichment_error) and returns a result dict:
            {'performed': bool, 'status': str, 'providers': [str], 'errors': [str]}
        """
        result = {'performed': False, 'status': 'Skipped', 'providers': [], 'errors': []}

        # Check if there's any active setting with auto_enrich
        active_settings = IOCEnrichmentSetting.objects.filter(is_active=True, auto_enrich=True)
        if not active_settings.exists():
            alert.enrichment_status = 'Skipped'
            alert.enrichment_updated_at = timezone.now()
            alert.enrichment_error = ''
            return result

        # Prepare the enrichment dict
        if not isinstance(alert.enrichment_data, dict):
            alert.enrichment_data = {}

        alert.enrichment_status = 'Running'
        providers_ok = []
        providers_failed = []
        errors = []

        # 1. IP Geolocation (IPInfo)
        ipinfo_setting = active_settings.filter(provider_name='IPInfo').first()
        if ipinfo_setting and alert.source_ip:
            try:
                # Basic IPInfo request without API key for free tier, or with key
                url = f"https://ipinfo.io/{alert.source_ip}/json"
                if ipinfo_setting.api_key:
                    url += f"?token={ipinfo_setting.api_key}"
                
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    alert.enrichment_data['IPInfo'] = {
                        'ip': data.get('ip'),
                        'city': data.get('city'),
                        'region': data.get('region'),
                        'country': data.get('country'),
                        'org': data.get('org'),
                        'loc': data.get('loc'),
                        'timestamp': timezone.now().isoformat()
                    }
                    providers_ok.append('IPInfo')
                else:
                    providers_failed.append('IPInfo')
                    errors.append(f'IPInfo HTTP {response.status_code}')
            except Exception as e:
                providers_failed.append('IPInfo')
                errors.append(f'IPInfo: {e}')
                logger.error(f"Failed to enrich IP {alert.source_ip} with IPInfo: {e}")

        # 2. VirusTotal File Hash
        vt_setting = active_settings.filter(provider_name='VirusTotal').first()
        file_hash = alert.file_hash_sha256 or alert.file_hash_md5
        if vt_setting and vt_setting.api_key and file_hash:
            cache_key = f"enrich_vt_{file_hash}"
            cached_data = cache.get(cache_key)
            if cached_data:
                alert.enrichment_data['VirusTotal'] = cached_data
                providers_ok.append('VirusTotal')
            else:
                try:
                    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
                    headers = {"x-apikey": vt_setting.api_key}
                    response = requests.get(url, headers=headers, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                        vt_data = {
                            'hash': file_hash,
                            'malicious': stats.get('malicious', 0),
                            'suspicious': stats.get('suspicious', 0),
                            'undetected': stats.get('undetected', 0),
                            'harmless': stats.get('harmless', 0),
                            'timestamp': timezone.now().isoformat()
                        }
                        alert.enrichment_data['VirusTotal'] = vt_data
                        cache.set(cache_key, vt_data, timeout=86400)
                        providers_ok.append('VirusTotal')
                    else:
                        providers_failed.append('VirusTotal')
                        errors.append(f'VirusTotal HTTP {response.status_code}')
                except Exception as e:
                    providers_failed.append('VirusTotal')
                    errors.append(f'VirusTotal: {e}')
                    logger.error(f"Failed to enrich hash {file_hash} with VirusTotal: {e}")

        # 3. AbuseIPDB
        abuseipdb_setting = active_settings.filter(provider_name='AbuseIPDB').first()
        if abuseipdb_setting and abuseipdb_setting.api_key and alert.source_ip:
            cache_key = f"enrich_abuseipdb_{alert.source_ip}"
            cached_data = cache.get(cache_key)
            if cached_data:
                alert.enrichment_data['AbuseIPDB'] = cached_data
                providers_ok.append('AbuseIPDB')
            else:
                try:
                    url = "https://api.abuseipdb.com/api/v2/check"
                    headers = {'Accept': 'application/json', 'Key': abuseipdb_setting.api_key}
                    params = {'ipAddress': alert.source_ip, 'maxAgeInDays': '90'}
                    response = requests.get(url, headers=headers, params=params, timeout=5)
                    if response.status_code == 200:
                        data = response.json().get('data', {})
                        abuse_data = {
                            'abuseConfidenceScore': data.get('abuseConfidenceScore', 0),
                            'totalReports': data.get('totalReports', 0),
                            'countryCode': data.get('countryCode', ''),
                            'domain': data.get('domain', ''),
                            'timestamp': timezone.now().isoformat()
                        }
                        alert.enrichment_data['AbuseIPDB'] = abuse_data
                        cache.set(cache_key, abuse_data, timeout=86400) # Cache for 24 hours
                        providers_ok.append('AbuseIPDB')
                    else:
                        providers_failed.append('AbuseIPDB')
                        errors.append(f'AbuseIPDB HTTP {response.status_code}')
                except Exception as e:
                    providers_failed.append('AbuseIPDB')
                    errors.append(f'AbuseIPDB: {e}')
                    logger.error(f"Failed to enrich IP {alert.source_ip} with AbuseIPDB: {e}")

        # 4. AlienVault OTX
        otx_setting = active_settings.filter(provider_name='OTX').first()
        if otx_setting and otx_setting.api_key:
            target = alert.source_ip or alert.file_hash_sha256 or alert.file_hash_md5
            indicator_type = 'IPv4' if alert.source_ip else 'file'
            if target:
                cache_key = f"enrich_otx_{indicator_type}_{target}"
                cached_data = cache.get(cache_key)
                if cached_data:
                    alert.enrichment_data['OTX'] = cached_data
                    providers_ok.append('OTX')
                else:
                    try:
                        url = f"https://otx.alienvault.com/api/v1/indicators/{indicator_type}/{target}/general"
                        headers = {'X-OTX-API-KEY': otx_setting.api_key}
                        response = requests.get(url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            data = response.json()
                            pulse_info = data.get('pulse_info', {})
                            otx_data = {
                                'pulse_count': pulse_info.get('count', 0),
                                'pulses': [p.get('name') for p in pulse_info.get('pulses', [])[:3]],
                                'timestamp': timezone.now().isoformat()
                            }
                            alert.enrichment_data['OTX'] = otx_data
                            cache.set(cache_key, otx_data, timeout=86400) # Cache for 24 hours
                            providers_ok.append('OTX')
                        else:
                            providers_failed.append('OTX')
                            errors.append(f'OTX HTTP {response.status_code}')
                    except Exception as e:
                        providers_failed.append('OTX')
                        errors.append(f'OTX: {e}')
                        logger.error(f"Failed to enrich {target} with OTX: {e}")

        # Derive overall status
        if providers_ok and providers_failed:
            status = 'Partial'
        elif providers_ok:
            status = 'Success'
        elif providers_failed:
            status = 'Failed'
        else:
            # Settings active but no provider had applicable inputs
            status = 'Skipped'

        alert.enrichment_status = status
        alert.enrichment_updated_at = timezone.now()
        alert.enrichment_error = '; '.join(errors)[:500]

        meta = alert.enrichment_data.get('_meta')
        if not isinstance(meta, dict):
            meta = {}
        meta.update({
            'status': status,
            'updated_at': alert.enrichment_updated_at.isoformat(),
            'providers_ok': providers_ok,
            'providers_failed': providers_failed,
        })
        alert.enrichment_data['_meta'] = meta

        result.update({
            'performed': bool(providers_ok),
            'status': status,
            'providers': providers_ok,
            'errors': errors,
        })
        return result

