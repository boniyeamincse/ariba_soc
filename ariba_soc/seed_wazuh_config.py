import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from wazuh_integration.models import WazuhConfiguration, WazuhManagerConfig

indexer_url = os.environ.get('WAZUH_INDEXER_URL', 'https://wazuh.indexer:9200')
indexer_user = os.environ.get('WAZUH_INDEXER_USERNAME', '')
indexer_password = os.environ.get('WAZUH_INDEXER_PASSWORD', '')
indexer_pattern = os.environ.get('WAZUH_INDEXER_INDEX_PATTERN', 'wazuh-alerts-*')
indexer_verify_ssl = os.environ.get('WAZUH_INDEXER_VERIFY_SSL', 'False').lower() == 'true'

manager_url = os.environ.get('WAZUH_API_URL', 'https://wazuh.manager:55000')
manager_user = os.environ.get('WAZUH_API_USERNAME', '')
manager_password = os.environ.get('WAZUH_API_PASSWORD', '')
manager_verify_ssl = os.environ.get('WAZUH_VERIFY_SSL', 'False').lower() == 'true'

# Seed Indexer Config (singleton: first row wins)
config = WazuhConfiguration.objects.first()
if config is None:
    config = WazuhConfiguration.objects.create(
        api_url=indexer_url,
        api_username=indexer_user,
        api_password=indexer_password,
        es_index_pattern=indexer_pattern,
        verify_ssl=indexer_verify_ssl,
        is_active=True,
    )
    print("Created new Wazuh Indexer config.")
else:
    config.api_url = indexer_url
    config.api_username = indexer_user
    config.api_password = indexer_password
    config.es_index_pattern = indexer_pattern
    config.verify_ssl = indexer_verify_ssl
    config.is_active = True
    config.save()
    print("Updated existing Wazuh Indexer config.")

# Seed Manager Config (singleton: first row wins)
mgr = WazuhManagerConfig.objects.first()
if mgr is None:
    mgr = WazuhManagerConfig.objects.create(
        api_url=manager_url,
        api_username=manager_user,
        api_password=manager_password,
        verify_ssl=manager_verify_ssl,
    )
    print("Created new Wazuh Manager config.")
else:
    mgr.api_url = manager_url
    mgr.api_username = manager_user
    mgr.api_password = manager_password
    mgr.verify_ssl = manager_verify_ssl
    mgr.save()
    print("Updated existing Wazuh Manager config.")

print("Wazuh configurations seeded successfully.")
