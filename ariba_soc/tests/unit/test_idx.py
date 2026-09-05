import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from wazuh_integration.services import IndexerClient
try:
    indexer = IndexerClient()
    print(indexer.test_connection())
    alerts = indexer.fetch_alerts()
    print("Alerts fetched:", len(alerts.get('data', {}).get('items', [])))
except Exception as e:
    print("Indexer Error:", e)
