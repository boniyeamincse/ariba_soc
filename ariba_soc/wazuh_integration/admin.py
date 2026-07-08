from django.contrib import admin
from .models import WazuhSyncLog, WazuhConfiguration

@admin.register(WazuhSyncLog)
class WazuhSyncLogAdmin(admin.ModelAdmin):
    list_display = ['started_at', 'status', 'alerts_fetched', 'alerts_created']
    list_filter = ['status']

@admin.register(WazuhConfiguration)
class WazuhConfigurationAdmin(admin.ModelAdmin):
    list_display = ['api_url', 'is_active', 'last_sync_at']
