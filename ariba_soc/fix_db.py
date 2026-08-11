import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

manager_url = os.environ.get('WAZUH_API_URL')
manager_user = os.environ.get('WAZUH_API_USERNAME')
manager_password = os.environ.get('WAZUH_API_PASSWORD')
indexer_url = os.environ.get('WAZUH_INDEXER_URL')
indexer_user = os.environ.get('WAZUH_INDEXER_USERNAME')
indexer_password = os.environ.get('WAZUH_INDEXER_PASSWORD')

if not all([manager_url, manager_user, manager_password, indexer_url, indexer_user, indexer_password]):
    sys.exit(
        'Set WAZUH_API_URL, WAZUH_API_USERNAME, WAZUH_API_PASSWORD, '
        'WAZUH_INDEXER_URL, WAZUH_INDEXER_USERNAME, WAZUH_INDEXER_PASSWORD env vars before running.'
    )

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM wazuh_integration_wazuhmanagerconfig;")
    cursor.execute("DELETE FROM wazuh_integration_wazuhconfiguration;")

from wazuh_integration.models import WazuhManagerConfig, WazuhConfiguration

verify_ssl = os.environ.get('WAZUH_VERIFY_SSL', 'False').lower() == 'true'
timeout = int(os.environ.get('WAZUH_API_TIMEOUT', '30'))

WazuhManagerConfig.objects.create(
    api_url=manager_url,
    api_username=manager_user,
    api_password=manager_password,
    verify_ssl=verify_ssl,
    timeout=timeout,
)
WazuhConfiguration.objects.create(
    api_url=indexer_url,
    api_username=indexer_user,
    api_password=indexer_password,
    verify_ssl=os.environ.get('WAZUH_INDEXER_VERIFY_SSL', 'False').lower() == 'true',
    timeout=timeout,
    sync_interval_minutes=int(os.environ.get('WAZUH_SYNC_INTERVAL_MINUTES', '5')),
    es_index_pattern=os.environ.get('WAZUH_INDEXER_INDEX_PATTERN', 'wazuh-alerts-*'),
    is_active=True,
)
print("Configs recreated successfully.")
