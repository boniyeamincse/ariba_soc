from django.contrib import admin
from .models import Alert, AlertComment, AlertAuditLog, AlertSource

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['alert_name', 'severity', 'status', 'verdict', 'assignee', 'alert_time']
    list_filter = ['severity', 'status', 'verdict', 'source']
    search_fields = ['alert_name', 'hostname', 'username', 'source_ip', 'rule_id']
    date_hierarchy = 'alert_time'

@admin.register(AlertComment)
class AlertCommentAdmin(admin.ModelAdmin):
    list_display = ['alert', 'user', 'comment_type', 'created_at']

@admin.register(AlertAuditLog)
class AlertAuditLogAdmin(admin.ModelAdmin):
    list_display = ['alert', 'user', 'action', 'created_at']
    list_filter = ['action']

@admin.register(AlertSource)
class AlertSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'is_active']
