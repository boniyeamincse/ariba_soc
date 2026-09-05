import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from wazuh_integration.models import WazuhManagerConfig
config = WazuhManagerConfig.objects.first()
if config:
    print(f"Manager URL: {config.api_url}")
    print(f"Manager Password decrypted: {config.api_password}")
else:
    print("No config found")
