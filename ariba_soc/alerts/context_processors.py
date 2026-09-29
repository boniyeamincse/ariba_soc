from .models import Alert, Notification
from accounts.models import SETTINGS_ALLOWED_ROLES
from settings_manager.models import SystemSetting, SeveritySettings, StatusSettings, VerdictSettings, AlarmSystemSetting

def _get_settings_roles():
    stored = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored:
        return [r.strip() for r in stored.split(',')]
    return SETTINGS_ALLOWED_ROLES


def user_alerts_context(request):
    if not request.user.is_authenticated:
        return {}
    profile = getattr(request.user, 'analyst_profile', None)
    role = profile.role if profile else ('ADMIN' if request.user.is_superuser else '')
    
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
    alarm_system = AlarmSystemSetting.load()
    
    return {
        'role': role,
        'my_assigned_count': Alert.objects.filter(assignee=request.user, status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'new_alerts_count': Alert.objects.filter(status='New').count(),
        'critical_alerts_count': Alert.objects.filter(severity='Critical', status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'settings_roles': _get_settings_roles(),
        'unread_notifications': unread_notifs,
        'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        'edit_severities': SeveritySettings.objects.filter(is_active=True).order_by('sort_order'),
        'edit_statuses': StatusSettings.objects.filter(is_active=True).order_by('sort_order'),
        'edit_verdicts': VerdictSettings.objects.filter(is_active=True).order_by('name'),
        'alarm_control': alarm_system,
        'alarm_is_active': alarm_system.is_active and alarm_system.is_enabled,
        'alarm_sound_url': alarm_system.sound_file.url if alarm_system.sound_file else '',
        'alarm_active_message': alarm_system.active_message,
    }
