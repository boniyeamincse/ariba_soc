from django.db import models
from django.contrib.auth.models import User
from config.fields import EncryptedCharField
from alerts.models import Alert


class WazuhSyncLog(models.Model):
    status = models.CharField(max_length=20, choices=[('Success', 'Success'), ('Failed', 'Failed'), ('Running', 'Running')], default='Running')
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    alerts_fetched = models.IntegerField(default=0)
    alerts_created = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"Sync {self.started_at} - {self.status}"


class WazuhConfiguration(models.Model):
    api_url = models.CharField(max_length=500, default='https://10.24.66.2:9200')
    api_username = models.CharField(max_length=200, blank=True)
    api_password = EncryptedCharField(max_length=500, blank=True)
    verify_ssl = models.BooleanField(default=False)
    timeout = models.IntegerField(default=30)
    sync_interval_minutes = models.IntegerField(default=5)
    es_index_pattern = models.CharField(max_length=200, default='wazuh-alerts-*', blank=True,
                                         help_text='Elasticsearch index pattern (e.g. wazuh-alerts-*)')
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Wazuh Indexer Configuration'

    def __str__(self):
        return f'Indexer Config - {self.api_url}'


class WazuhManagerConfig(models.Model):
    api_url = models.CharField(max_length=500, default='https://10.24.66.2:55000')
    api_username = models.CharField(max_length=200, blank=True)
    api_password = EncryptedCharField(max_length=500, blank=True)
    verify_ssl = models.BooleanField(default=False)
    timeout = models.IntegerField(default=30)

    class Meta:
        verbose_name = 'Wazuh Manager Configuration'

    def __str__(self):
        return f'Manager Config - {self.api_url}'


class ActiveResponseExecution(models.Model):
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PENDING', 'Pending'),
    ]

    COMMAND_CHOICES = [
        ('firewall-drop', 'Block IP (Firewall Drop)'),
        ('host-deny', 'Deny Host (TCP Wrappers)'),
        ('disable-account', 'Disable User Account'),
        ('restart-wazuh', 'Restart Wazuh Agent'),
        ('custom', 'Custom Active Response'),
    ]

    alert = models.ForeignKey(Alert, on_delete=models.SET_NULL, null=True, blank=True, related_name='active_responses')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    command = models.CharField(max_length=100, choices=COMMAND_CHOICES)
    target_agent_id = models.CharField(max_length=50)
    target_agent_name = models.CharField(max_length=255, blank=True)
    target_ip = models.CharField(max_length=100, blank=True)
    target_user = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    response_message = models.TextField(blank=True)
    response_json = models.JSONField(default=dict, blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']
        verbose_name = 'Active Response Execution'
        verbose_name_plural = 'Active Response Executions'

    def __str__(self):
        return f"{self.command} on agent {self.target_agent_id} ({self.status})"

