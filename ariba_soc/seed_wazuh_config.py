import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from wazuh_integration.models import WazuhConfiguration, WazuhManagerConfig

# Seed Indexer Config (singleton: first row wins)
config = WazuhConfiguration.objects.first()
if config is None:
    config = WazuhConfiguration.objects.create(
        api_url='https://wazuh.indexer:9200',
        api_username='admin',
        api_password='SecretPassword',
        es_index_pattern='wazuh-alerts-*',
        verify_ssl=False,
        is_active=True,
    )
    print("Created new Wazuh Indexer config.")
else:
    config.api_url = 'https://wazuh.indexer:9200'
    config.api_username = 'admin'
    config.api_password = 'SecretPassword'
    config.es_index_pattern = 'wazuh-alerts-*'
    config.verify_ssl = False
    config.is_active = True
    config.save()
    print("Updated existing Wazuh Indexer config.")

# Seed Manager Config (singleton: first row wins)
mgr = WazuhManagerConfig.objects.first()
if mgr is None:
    mgr = WazuhManagerConfig.objects.create(
        api_url='https://wazuh.manager:55000',
        api_username='wazuh-wui',
        api_password='MyS3cr37P450r.*-',
        verify_ssl=False,
    )
    print("Created new Wazuh Manager config.")
else:
    mgr.api_url = 'https://wazuh.manager:55000'
    mgr.api_username = 'wazuh-wui'
    mgr.api_password = 'MyS3cr37P450r.*-'
    mgr.verify_ssl = False
    mgr.save()
    print("Updated existing Wazuh Manager config.")

print("Wazuh configurations seeded successfully.")
