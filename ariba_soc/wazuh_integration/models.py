from django.db import models

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
    api_url = models.CharField(max_length=500, default='https://localhost:55000')
    api_username = models.CharField(max_length=200, blank=True)
    api_password = models.CharField(max_length=500, blank=True)
    verify_ssl = models.BooleanField(default=False)
    timeout = models.IntegerField(default=30)
    sync_interval_minutes = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Wazuh Configuration'

    def __str__(self):
        return f'Wazuh Config - {self.api_url}'
