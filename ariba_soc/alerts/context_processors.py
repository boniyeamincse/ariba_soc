from .models import Alert

def user_alerts_context(request):
    if not request.user.is_authenticated:
        return {}
    role = getattr(request.user.analyst_profile, 'role', '')
    return {
        'my_assigned_count': Alert.objects.filter(assignee=request.user, status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'new_alerts_count': Alert.objects.filter(status='New').count(),
        'critical_alerts_count': Alert.objects.filter(severity='Critical', status__in=['New', 'In Progress', 'Awaiting Action']).count(),
        'settings_roles': ['SOC_MGR', 'SOC_ENG', 'ADMIN'],
    }
