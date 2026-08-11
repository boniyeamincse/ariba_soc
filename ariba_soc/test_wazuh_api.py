import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'
django.setup()

from wazuh_integration.models import WazuhManagerConfig
from wazuh_integration.services import ManagerClient

config, created = WazuhManagerConfig.objects.get_or_create(id=1)
config.api_url = 'https://10.24.66.2:55000' # Wazuh API is typically 55000
config.api_username = 'soc-api-user'
config.api_password = 'Care@#$1718'
config.verify_ssl = False
config.timeout = 15
config.save()

print("Config saved to database (using port 55000).")

client = ManagerClient(config)
try:
    token = client.authenticate()
    print("SUCCESS: Authenticated to Wazuh API on 55000! Token received.")
except Exception as e:
    print("FAILED on 55000:", str(e))
    
    # Try port 5000 just in case it was not a typo
    config.api_url = 'https://10.24.66.2:5000'
    config.save()
    print("\nTrying port 5000 as specified by user...")
    client = ManagerClient(config)
    try:
        token = client.authenticate()
        print("SUCCESS: Authenticated to Wazuh API on 5000! Token received.")
    except Exception as e2:
        print("FAILED on 5000:", str(e2))

