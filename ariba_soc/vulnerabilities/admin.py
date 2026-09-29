from django.contrib import admin
from .models import VulnerabilityCase, VulnerabilityAuditLog


class VulnerabilityAuditLogInLine(admin.TabularInline):
    model = VulnerabilityAuditLog
    extra = 0
    readonly_fields = ['created_at']


@admin.register(VulnerabilityCase)
class VulnerabilityCaseAdmin(admin.ModelAdmin):
    list_display = [
        'cve_id', 'package_name', 'severity', 'cvss_score',
        'status', 'priority', 'agent_id', 'owner', 'created_at'
    ]
    list_filter = ['status', 'priority', 'severity', 'risk_accepted']
    search_fields = ['cve_id', 'package_name', 'vulnerability_key', 'agent_id']
    inlines = [VulnerabilityAuditLogInLine]
    readonly_fields = ['vulnerability_key', 'created_at', 'updated_at']


@admin.register(VulnerabilityAuditLog)
class VulnerabilityAuditLogAdmin(admin.ModelAdmin):
    list_display = ['vulnerability', 'user', 'action', 'created_at']
    list_filter = ['action']
    search_fields = ['vulnerability__cve_id', 'user__username', 'action']
