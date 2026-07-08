from django.db import models
from django.contrib.auth.models import User


class AuditLog(models.Model):
    ACTIONS = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('ALERT_CREATED', 'Alert Created'),
        ('ALERT_UPDATED', 'Alert Updated'),
        ('ALERT_CLOSED', 'Alert Closed'),
        ('ALERT_ESCALATED', 'Alert Escalated'),
        ('ALERT_ASSIGNED', 'Alert Assigned'),
        ('REPORT_GENERATED', 'Report Generated'),
        ('USER_CREATED', 'User Created'),
        ('USER_UPDATED', 'User Updated'),
        ('PERMISSION_CHANGED', 'Permission Changed'),
        ('WAZUH_SYNC', 'Wazuh Sync'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50, choices=ACTIONS)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=50, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"{self.user} - {self.action} - {self.created_at}"
