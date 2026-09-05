from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.models import RolePermission


def hunting_permission_required(permission_name):
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


def require_hunting_access(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'analyst_profile'):
            return JsonResponse({'error': 'Access denied'}, status=403)
        profile = request.user.analyst_profile
        if not profile.is_active:
            return JsonResponse({'error': 'Access denied'}, status=403)
        has_basic = RolePermission.has_permission(profile.role, 'can_use_basic_hunting')
        has_advanced = RolePermission.has_permission(profile.role, 'can_use_advanced_hunting')
        if not has_basic and not has_advanced:
            return JsonResponse({'error': 'Access denied'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper
