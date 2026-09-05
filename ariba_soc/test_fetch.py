import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from wazuh_integration.services import IndexerClient, ManagerClient
try:
    manager = ManagerClient()
    agents = manager.fetch_agents()
    print("Agents connected:", agents)
except Exception as e:
    print("Manager Error:", e)

try:
    indexer = IndexerClient()
    print("Indexer health:", indexer.test_connection())
    alerts = indexer.fetch_alerts()
    print("Alerts fetched:", len(alerts.get('data', {}).get('items', [])))
except Exception as e:
    print("Indexer Error:", e)
