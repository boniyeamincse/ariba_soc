from django.contrib import admin
from .models import WazuhSyncLog, WazuhConfiguration, WazuhManagerConfig, ActiveResponseExecution

@admin.register(WazuhSyncLog)
class WazuhSyncLogAdmin(admin.ModelAdmin):
    list_display = ['started_at', 'status', 'alerts_fetched', 'alerts_created']
    list_filter = ['status']

@admin.register(WazuhConfiguration)
class WazuhConfigurationAdmin(admin.ModelAdmin):
    list_display = ['api_url', 'is_active', 'last_sync_at']

@admin.register(WazuhManagerConfig)
class WazuhManagerConfigAdmin(admin.ModelAdmin):
    list_display = ['api_url', 'timeout']

@admin.register(ActiveResponseExecution)
class ActiveResponseExecutionAdmin(admin.ModelAdmin):
    list_display = ['command', 'target_agent_id', 'target_ip', 'status', 'executed_at', 'user', 'alert']
    list_filter = ['command', 'status']
    search_fields = ['target_agent_id', 'target_ip', 'target_user', 'response_message']

