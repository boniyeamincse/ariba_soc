import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("DELETE FROM wazuh_integration_wazuhmanagerconfig;")
    cursor.execute("DELETE FROM wazuh_integration_wazuhconfiguration;")

from wazuh_integration.models import WazuhManagerConfig, WazuhConfiguration
WazuhManagerConfig.objects.create(
    api_url='https://10.24.66.2:55000',
    api_username='soc-api-user',
    api_password='Care@#$1718',
    verify_ssl=False,
    timeout=30
)
WazuhConfiguration.objects.create(
    api_url='https://10.24.66.2:9200',
    api_username='soc-api-user',
    api_password='Care@#$1718',
    verify_ssl=False,
    timeout=30,
    sync_interval_minutes=5,
    es_index_pattern='wazuh-alerts-*',
    is_active=True
)
print("Configs recreated successfully.")
