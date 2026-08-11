import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model

username = os.environ.get('DJANGO_ADMIN_USERNAME')
password = os.environ.get('DJANGO_ADMIN_PASSWORD')
email = os.environ.get('DJANGO_ADMIN_EMAIL', f'{username}@example.com' if username else None)

if not username or not password:
    sys.exit('Set DJANGO_ADMIN_USERNAME and DJANGO_ADMIN_PASSWORD env vars before running.')

User = get_user_model()
try:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.save()
    print(f"Admin password reset for {username}")
except User.DoesNotExist:
    User.objects.create_superuser(username, email, password)
    print(f"Admin user created: {username}")
