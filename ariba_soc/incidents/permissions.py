from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.models import RolePermission


INCIDENT_PERMISSIONS = {
    'can_view_incidents': ['L1', 'L2', 'L3', 'SOC_ENG', 'SOC_MGR', 'ADMIN', 'VIEWER'],
    'can_create_incident': ['L2', 'L3', 'SOC_MGR', 'ADMIN'],
    'can_assign_incident': ['L2', 'L3', 'SOC_MGR', 'ADMIN'],
    'can_manage_incident': ['L2', 'L3', 'SOC_MGR', 'ADMIN'],
    'can_close_incident': ['L3', 'SOC_MGR', 'ADMIN'],
    'can_reopen_incident': ['L3', 'SOC_MGR', 'ADMIN'],
    'can_link_incident_alerts': ['L2', 'L3', 'SOC_ENG', 'SOC_MGR', 'ADMIN'],
}


def incident_permission_required(permission_name):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if not hasattr(request.user, 'analyst_profile'):
                return JsonResponse({'error': 'Access denied'}, status=403)
            profile = request.user.analyst_profile
            if not profile.is_active:
                return JsonResponse({'error': 'Access denied'}, status=403)
            if not RolePermission.has_permission(profile.role, permission_name):
                return JsonResponse({'error': 'Access denied'}, status=403)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_incident_access(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'analyst_profile'):
            return JsonResponse({'error': 'Access denied'}, status=403)
        profile = request.user.analyst_profile
        if not profile.is_active:
            return JsonResponse({'error': 'Access denied'}, status=403)
        if profile.role in ('MONITOR',):
            return JsonResponse({'error': 'Access denied'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
