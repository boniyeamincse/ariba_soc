import requests
from django.utils import timezone
from settings_manager.models import IOCEnrichmentSetting
import logging

logger = logging.getLogger(__name__)

class EnrichmentService:
    @staticmethod
    def enrich_alert(alert):
        """
        Enriches an alert if there are active IOCEnrichmentSettings and auto_enrich is enabled.
        Returns True if enrichment was performed, False otherwise.
        """
        enrichment_performed = False
        
        # Check if there's any active setting with auto_enrich
        active_settings = IOCEnrichmentSetting.objects.filter(is_active=True, auto_enrich=True)
        if not active_settings.exists():
            return False

        # Prepare the enrichment dict
        if not isinstance(alert.enrichment_data, dict):
            alert.enrichment_data = {}

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
                    enrichment_performed = True
            except Exception as e:
                logger.error(f"Failed to enrich IP {alert.source_ip} with IPInfo: {e}")

        # 2. VirusTotal File Hash
        vt_setting = active_settings.filter(provider_name='VirusTotal').first()
        # Prefer SHA256, fallback to MD5
        file_hash = alert.file_hash_sha256 or alert.file_hash_md5
        if vt_setting and vt_setting.api_key and file_hash:
            try:
                url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
                headers = {
                    "x-apikey": vt_setting.api_key
                }
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    stats = data.get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                    alert.enrichment_data['VirusTotal'] = {
                        'hash': file_hash,
                        'malicious': stats.get('malicious', 0),
                        'suspicious': stats.get('suspicious', 0),
                        'undetected': stats.get('undetected', 0),
                        'harmless': stats.get('harmless', 0),
                        'timestamp': timezone.now().isoformat()
                    }
                    enrichment_performed = True
            except Exception as e:
                logger.error(f"Failed to enrich hash {file_hash} with VirusTotal: {e}")

        if enrichment_performed:
            # We don't call save() here to prevent recursive/unnecessary DB hits if being called before initial save.
            # The caller is responsible for saving the alert.
            pass

        return enrichment_performed
