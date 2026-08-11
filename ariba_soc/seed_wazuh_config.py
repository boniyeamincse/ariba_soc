import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from wazuh_integration.models import WazuhConfiguration, WazuhManagerConfig

# Seed Indexer Config
config, created = WazuhConfiguration.objects.get_or_create(
    name='Wazuh Indexer Docker',
    defaults={
        'api_url': 'https://wazuh.indexer:9200',
        'api_username': 'admin',
        'api_password': 'SecretPassword',
        'es_index_pattern': 'wazuh-alerts-*',
        'verify_ssl': False,
        'is_active': True,
    }
)
if not created:
    config.api_url = 'https://wazuh.indexer:9200'
    config.api_username = 'admin'
    config.api_password = 'SecretPassword'
    config.verify_ssl = False
    config.save()
    print("Updated existing Wazuh Indexer config.")
else:
    print("Created new Wazuh Indexer config.")

# Seed Manager Config
mgr, mgr_created = WazuhManagerConfig.objects.get_or_create(
    name='Wazuh Manager Docker',
    defaults={
        'api_url': 'https://wazuh.manager:55000',
        'api_username': 'wazuh-wui',
        'api_password': 'MyS3cr37P450r.*-',
        'verify_ssl': False,
        'is_active': True,
    }
)
if not mgr_created:
    mgr.api_url = 'https://wazuh.manager:55000'
    mgr.api_username = 'wazuh-wui'
    mgr.api_password = 'MyS3cr37P450r.*-'
    mgr.verify_ssl = False
    mgr.save()
    print("Updated existing Wazuh Manager config.")
else:
    print("Created new Wazuh Manager config.")

print("Wazuh configurations seeded successfully.")
