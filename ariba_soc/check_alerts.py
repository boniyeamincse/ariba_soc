import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from alerts.models import Alert
from wazuh_integration.services import fetch_wazuh_alerts

count = Alert.objects.count()
print(f"Total alerts in database currently: {count}")

try:
    print("Attempting to fetch Wazuh alerts...")
    result = fetch_wazuh_alerts(time_range='24h')
    print(f"Sync result: {result}")
    
    new_count = Alert.objects.count()
    print(f"Total alerts in database after sync: {new_count}")
except Exception as e:
    print(f"Error fetching alerts: {e}")
