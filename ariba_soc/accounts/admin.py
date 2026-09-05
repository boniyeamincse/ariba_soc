from django.contrib import admin
from .models import AnalystProfile, RolePermission

@admin.register(AnalystProfile)
class AnalystProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'team', 'is_active']
    list_filter = ['role', 'team', 'is_active']
    search_fields = ['user__username', 'user__email']

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role']
