from django.contrib import admin
from .models import AnalystProfile, RolePermission, SocTeam

@admin.register(SocTeam)
class SocTeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'lead', 'shift_type', 'is_active', 'created_at']
    list_filter = ['tier', 'shift_type', 'is_active']
    search_fields = ['name', 'description', 'lead__username']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(AnalystProfile)
class AnalystProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'soc_team', 'team', 'is_active']
    list_filter = ['role', 'soc_team', 'team', 'is_active']
    search_fields = ['user__username', 'user__email']

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ['role']
