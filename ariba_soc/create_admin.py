import os
import sys
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'
django.setup()

username = os.environ.get('DJANGO_ADMIN_USERNAME')
email = os.environ.get('DJANGO_ADMIN_EMAIL')
password = os.environ.get('DJANGO_ADMIN_PASSWORD')

if not all([username, email, password]):
    sys.exit('Set DJANGO_ADMIN_USERNAME, DJANGO_ADMIN_EMAIL, DJANGO_ADMIN_PASSWORD env vars before running.')

User = get_user_model()
if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(username, email, password)
    print(f"Created superuser {username}")
else:
    user = User.objects.get(username=username)
    user.set_password(password)
    user.save()
    print(f"Reset password for existing {username}")

# Also assign a role to analyst profile if needed
from accounts.models import AnalystProfile
profile, _ = AnalystProfile.objects.get_or_create(user=user)
profile.role = 'ADMIN'
profile.save()
print("Set role to ADMIN")
