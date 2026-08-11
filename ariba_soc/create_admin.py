import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['DATABASE_ENGINE'] = 'django.db.backends.sqlite3'
django.setup()

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    user = User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    print("Created superuser admin / adminpass")
else:
    user = User.objects.get(username='admin')
    user.set_password('adminpass')
    user.save()
    print("Reset password for existing admin / adminpass")

# Also assign a role to analyst profile if needed
from accounts.models import AnalystProfile
profile, _ = AnalystProfile.objects.get_or_create(user=user)
profile.role = 'ADMIN'
profile.save()
print("Set role to ADMIN")

