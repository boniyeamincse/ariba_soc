from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

ROLE_CHOICES = [
    ('L1', 'SOC L1 Analyst'),
    ('L2', 'SOC L2 Analyst'),
    ('L3', 'SOC L3 Analyst'),
    ('SOC_ENG', 'SOC Engineer'),
    ('SOC_MGR', 'SOC Manager'),
    ('ADMIN', 'Admin'),
    ('VIEWER', 'Viewer'),
    ('MONITOR', 'Monitor'),
]

SETTINGS_ALLOWED_ROLES = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
WAZUH_ALLOWED_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR', 'L1', 'L2', 'L3']

TEAM_CHOICES = [
    ('L1', 'L1 Team'),
    ('L2', 'L2 Team'),
    ('L3', 'L3 Team'),
    ('ENG', 'Engineering'),
    ('MANAGEMENT', 'Management'),
]


class AnalystProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='analyst_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='L1')
    team = models.CharField(max_length=20, choices=TEAM_CHOICES, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Analyst Profile'
        verbose_name_plural = 'Analyst Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def has_permission(self, perm):
        return RolePermission.has_permission(self.role, perm)


class RolePermission(models.Model):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    can_view_alerts = models.BooleanField(default=True)
    can_assign_self = models.BooleanField(default=True)
    can_assign_others = models.BooleanField(default=False)
    can_change_status = models.BooleanField(default=True)
    can_change_severity = models.BooleanField(default=False)
    can_change_verdict = models.BooleanField(default=True)
    can_close_alert = models.BooleanField(default=False)
    can_escalate_alert = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_manage_wazuh = models.BooleanField(default=False)
    can_view_audit_logs = models.BooleanField(default=False)
    can_archive = models.BooleanField(default=False)
    can_reassign = models.BooleanField(default=False)
    can_add_remediation = models.BooleanField(default=False)
    can_mark_incident = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Role Permission'
        verbose_name_plural = 'Role Permissions'

    def __str__(self):
        return f"Permissions for {self.get_role_display()}"

    @staticmethod
    def has_permission(role, perm):
        try:
            rp = RolePermission.objects.get(role=role)
            return getattr(rp, perm, False)
        except RolePermission.DoesNotExist:
            return False


@receiver(post_save, sender=User)
def create_analyst_profile(sender, instance, created, **kwargs):
    if created:
        AnalystProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_analyst_profile(sender, instance, **kwargs):
    if hasattr(instance, 'analyst_profile'):
        instance.analyst_profile.save()
