from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'object_type', 'created_at']
    list_filter = ['action']
    search_fields = ['user__username']
