from django.contrib import admin
from .models import (
    AlertSourceSettings, SeveritySettings, StatusSettings, VerdictSettings,
    SLASettings, EscalationRule, NotificationSetting, ReportSetting,
    DashboardSetting, AuditLogSetting, SystemSetting, SettingAuditLog,
    AlarmSetting, AlarmSystemSetting, IOCEnrichmentSetting, AlertAggregationSetting,
    AlertSuppressionRule
)

@admin.register(AlertSourceSettings)
class AlertSourceSettingsAdmin(admin.ModelAdmin): list_display = ['name', 'source_type', 'is_active']

@admin.register(SeveritySettings)
class SeveritySettingsAdmin(admin.ModelAdmin): list_display = ['name', 'score', 'color', 'is_active']

@admin.register(StatusSettings)
class StatusSettingsAdmin(admin.ModelAdmin): list_display = ['name', 'is_final', 'is_active']

@admin.register(VerdictSettings)
class VerdictSettingsAdmin(admin.ModelAdmin): list_display = ['name', 'requires_comment', 'is_active']

@admin.register(SLASettings)
class SLASettingsAdmin(admin.ModelAdmin): list_display = ['severity', 'acknowledge_minutes', 'resolve_minutes']

@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin): list_display = ['rule_name', 'severity_condition', 'is_active']

@admin.register(NotificationSetting)
class NotificationSettingAdmin(admin.ModelAdmin): list_display = ['name', 'event_type', 'channel', 'is_active']

@admin.register(ReportSetting)
class ReportSettingAdmin(admin.ModelAdmin): list_display = ['name', 'report_type', 'schedule', 'is_active']

@admin.register(DashboardSetting)
class DashboardSettingAdmin(admin.ModelAdmin): list_display = ['role', 'default_page']

@admin.register(AuditLogSetting)
class AuditLogSettingAdmin(admin.ModelAdmin): list_display = ['action_type', 'log_enabled', 'retention_days']

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin): list_display = ['key', 'value']

@admin.register(SettingAuditLog)
class SettingAuditLogAdmin(admin.ModelAdmin): list_display = ['user', 'action', 'created_at']

@admin.register(AlarmSetting)
class AlarmSettingAdmin(admin.ModelAdmin):
    list_display = ['severity', 'is_enabled', 'sort_order', 'updated_at']
    list_editable = ['is_enabled', 'sort_order']

@admin.register(AlarmSystemSetting)
class AlarmSystemSettingAdmin(admin.ModelAdmin):
    list_display = ['is_enabled', 'is_active', 'active_severity', 'active_alert_name', 'triggered_at']

@admin.register(IOCEnrichmentSetting)
class IOCEnrichmentSettingAdmin(admin.ModelAdmin):
    list_display = ['provider_name', 'is_active', 'auto_enrich', 'created_at']
    list_filter = ['is_active', 'auto_enrich']

@admin.register(AlertAggregationSetting)
class AlertAggregationSettingAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_enabled', 'window_minutes', 'max_events_per_alert', 'updated_at']
    list_display_links = ['id']
    list_editable = ['is_enabled', 'window_minutes']


@admin.register(AlertSuppressionRule)
class AlertSuppressionRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'action', 'rule_id', 'source_ip', 'hostname', 'is_active', 'match_count', 'expires_at']
    list_filter = ['action', 'is_active']
    search_fields = ['name', 'rule_id', 'source_ip', 'destination_ip', 'hostname', 'agent_id', 'username']


