from django.test import TestCase
from accounts.models import RolePermission


class RolePermissionTests(TestCase):
    def test_l1_has_basic_hunting(self):
        rp, _ = RolePermission.objects.get_or_create(role='L1')
        rp.can_use_basic_hunting = True
        rp.can_use_advanced_hunting = False
        rp.save()
        self.assertTrue(RolePermission.has_permission('L1', 'can_use_basic_hunting'))
        self.assertFalse(RolePermission.has_permission('L1', 'can_use_advanced_hunting'))

    def test_l2_has_both_hunting(self):
        rp, _ = RolePermission.objects.get_or_create(role='L2')
        rp.can_use_basic_hunting = True
        rp.can_use_advanced_hunting = True
        rp.save()
        self.assertTrue(RolePermission.has_permission('L2', 'can_use_basic_hunting'))
        self.assertTrue(RolePermission.has_permission('L2', 'can_use_advanced_hunting'))

    def test_viewer_has_no_hunting(self):
        rp, _ = RolePermission.objects.get_or_create(role='VIEWER')
        rp.can_use_basic_hunting = False
        rp.can_use_advanced_hunting = False
        rp.save()
        self.assertFalse(RolePermission.has_permission('VIEWER', 'can_use_basic_hunting'))
        self.assertFalse(RolePermission.has_permission('VIEWER', 'can_use_advanced_hunting'))

    def test_nonexistent_role_returns_false(self):
        self.assertFalse(RolePermission.has_permission('FAKE_ROLE', 'can_use_basic_hunting'))
