from django.contrib import admin
from .models import Incident, IncidentAlert, IncidentTimeline, IncidentNote


class IncidentAlertInline(admin.TabularInline):
    model = IncidentAlert
    extra = 0
    raw_id_fields = ['alert']


class IncidentTimelineInline(admin.TabularInline):
    model = IncidentTimeline
    extra = 0
    readonly_fields = ['created_at']


class IncidentNoteInline(admin.TabularInline):
    model = IncidentNote
    extra = 0
    readonly_fields = ['created_at']


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = [
        'incident_number', 'title', 'severity', 'status',
        'priority', 'owner', 'current_tier', 'created_at'
    ]
    list_filter = ['status', 'severity', 'priority', 'current_tier']
    search_fields = ['incident_number', 'title', 'description', 'affected_service']
    inlines = [IncidentAlertInline, IncidentTimelineInline, IncidentNoteInline]
    readonly_fields = ['incident_number', 'created_at', 'updated_at']


@admin.register(IncidentAlert)
class IncidentAlertAdmin(admin.ModelAdmin):
    list_display = ['incident', 'alert', 'is_primary', 'linked_by', 'linked_at']
    list_filter = ['is_primary']
    search_fields = ['incident__incident_number', 'alert__alert_name']


@admin.register(IncidentTimeline)
class IncidentTimelineAdmin(admin.ModelAdmin):
    list_display = ['incident', 'event_type', 'actor', 'title', 'created_at']
    list_filter = ['event_type']
    search_fields = ['incident__incident_number', 'title', 'description']


@admin.register(IncidentNote)
class IncidentNoteAdmin(admin.ModelAdmin):
    list_display = ['incident', 'note_type', 'created_by', 'created_at']
    list_filter = ['note_type']
    search_fields = ['incident__incident_number', 'note']
