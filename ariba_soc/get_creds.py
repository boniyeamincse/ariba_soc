import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    user = User.objects.get(username='admin')
    user.set_password('adminpass')
    user.save()
    print("Admin password reset to 'adminpass'")
except User.DoesNotExist:
    User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')
    print("Admin user created with password 'adminpass'")
