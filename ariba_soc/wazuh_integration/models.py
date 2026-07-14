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
    API_TYPE_CHOICES = [
        ('wazuh_api', 'Wazuh REST API (port 55000)'),
        ('elasticsearch', 'Elasticsearch / OpenSearch (port 9200)'),
    ]
    api_type = models.CharField(max_length=20, choices=API_TYPE_CHOICES, default='wazuh_api')
    api_url = models.CharField(max_length=500, default='https://localhost:55000')
    api_username = models.CharField(max_length=200, blank=True)
    api_password = models.CharField(max_length=500, blank=True)
    verify_ssl = models.BooleanField(default=False)
    timeout = models.IntegerField(default=30)
    sync_interval_minutes = models.IntegerField(default=5)
    es_index_pattern = models.CharField(max_length=200, default='wazuh-alerts-*', blank=True,
                                         help_text='Elasticsearch index pattern (e.g. wazuh-alerts-*)')
    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Wazuh Configuration'

    def __str__(self):
        return f'Wazuh Config ({self.get_api_type_display()}) - {self.api_url}'
