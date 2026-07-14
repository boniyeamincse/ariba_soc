from django.test import TestCase
from django.contrib.auth.models import User
from .models import AnalystProfile, RolePermission


class AnalystProfileSignalTest(TestCase):
    def test_profile_created_on_user_create(self):
        user = User.objects.create_user(username='testuser', password='pass')
        self.assertTrue(hasattr(user, 'analyst_profile'))
        self.assertEqual(user.analyst_profile.role, 'L1')

    def test_str_method(self):
        user = User.objects.create_user(username='testuser', password='pass')
        self.assertIn('testuser', str(user.analyst_profile))
