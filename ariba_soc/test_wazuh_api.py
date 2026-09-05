import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'
django.setup()

from wazuh_integration.models import WazuhManagerConfig
from wazuh_integration.services import ManagerClient

api_url = os.environ.get('WAZUH_API_URL')
api_username = os.environ.get('WAZUH_API_USERNAME')
api_password = os.environ.get('WAZUH_API_PASSWORD')

if not all([api_url, api_username, api_password]):
    sys.exit('Set WAZUH_API_URL, WAZUH_API_USERNAME, WAZUH_API_PASSWORD env vars before running.')

config, created = WazuhManagerConfig.objects.get_or_create(id=1)
config.api_url = api_url
config.api_username = api_username
config.api_password = api_password
config.verify_ssl = os.environ.get('WAZUH_VERIFY_SSL', 'False').lower() == 'true'
config.timeout = int(os.environ.get('WAZUH_API_TIMEOUT', '15'))
config.save()

print(f"Config saved to database ({config.api_url}).")

client = ManagerClient(config)
try:
    token = client.authenticate()
    print("SUCCESS: Authenticated to Wazuh API! Token received.")
except Exception as e:
    print("FAILED:", str(e))
