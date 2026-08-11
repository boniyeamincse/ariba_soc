from django.db import models
from django_cryptography.fields import encrypt


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
    api_password = encrypt(models.CharField(max_length=500, blank=True))
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
    api_password = encrypt(models.CharField(max_length=500, blank=True))
    verify_ssl = models.BooleanField(default=False)
    timeout = models.IntegerField(default=30)

    class Meta:
        verbose_name = 'Wazuh Manager Configuration'

    def __str__(self):
        return f'Manager Config - {self.api_url}'
