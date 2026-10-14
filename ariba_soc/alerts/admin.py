from django.contrib import admin
from .models import Alert, AlertComment, AlertAuditLog, AlertSource, AlertEscalation, AlertTransition, Notification, AlertAttachment, AlertWatcher, FalsePositiveReport

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['alert_name', 'severity', 'status', 'verdict', 'assigned_team', 'assignee', 'alert_time']
    list_filter = ['severity', 'status', 'verdict', 'assigned_team', 'source']
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

@admin.register(AlertEscalation)
class AlertEscalationAdmin(admin.ModelAdmin):
    list_display = ['alert', 'source_tier', 'target_tier', 'escalated_by', 'escalation_status', 'escalated_at']
    list_filter = ['escalation_status', 'source_tier', 'target_tier']

@admin.register(AlertTransition)
class AlertTransitionAdmin(admin.ModelAdmin):
    list_display = ['alert', 'from_state', 'to_state', 'action', 'actor', 'created_at']
    list_filter = ['action']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'message', 'is_read', 'created_at']
    list_filter = ['is_read']


@admin.register(FalsePositiveReport)
class FalsePositiveReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'alert', 'rule_id', 'reported_by', 'created_at']
    list_filter = ['rule_id']
    search_fields = ['rule_id', 'reason']
