from .models import Alert, Notification
from accounts.models import SETTINGS_ALLOWED_ROLES
from settings_manager.models import SystemSetting

def _get_settings_roles():
    stored = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored:
        return [r.strip() for r in stored.split(',')]
    return SETTINGS_ALLOWED_ROLES


def user_alerts_context(request):
    if not request.user.is_authenticated:
        return {}
    role = getattr(request.user.analyst_profile, 'role', '')
    
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
    
    return {
        'my_assigned_count': Alert.objects.filter(assignee=request.user, status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'new_alerts_count': Alert.objects.filter(status='New').count(),
        'critical_alerts_count': Alert.objects.filter(severity='Critical', status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'settings_roles': _get_settings_roles(),
        'unread_notifications': unread_notifs,
        'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count(),
    }
