from functools import wraps
from django.http import JsonResponse
from django.shortcuts import render
from django.core.exceptions import PermissionDenied


TIER_ORDER = {'L1': 1, 'L2': 2, 'L3': 3, 'SOC_ENG': 3, 'SOC_MGR': 4, 'ADMIN': 5, 'VIEWER': 0, 'MONITOR': 0}


def _get_user_role(user):
    profile = getattr(user, 'analyst_profile', None)
    if not profile:
        return None
    return profile.role


def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json'


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.conf import settings
                return JsonResponse({'error': 'Authentication required'}, status=401) if _is_ajax(request) else None
            role = _get_user_role(request.user)
            if role not in allowed_roles:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Forbidden', 'detail': 'You do not have access to this resource.'}, status=403)
                raise PermissionDenied('You do not have access to this dashboard.')
            if getattr(request.user, 'analyst_profile', None) and not request.user.analyst_profile.is_active:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Account inactive'}, status=403)
                raise PermissionDenied('Your account is inactive.')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def minimum_soc_tier(min_tier):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                return None
            role = _get_user_role(request.user)
            if not role:
                if _is_ajax(request):
                    return JsonResponse({'error': 'No role assigned'}, status=403)
                raise PermissionDenied('No role assigned to your account.')
            user_level = TIER_ORDER.get(role, 0)
            required_level = TIER_ORDER.get(min_tier, 0)
            if user_level < required_level:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Forbidden', 'detail': f'Minimum tier {min_tier} required.'}, status=403)
                raise PermissionDenied(f'Minimum tier {min_tier} required.')
            if getattr(request.user, 'analyst_profile', None) and not request.user.analyst_profile.is_active:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Account inactive'}, status=403)
                raise PermissionDenied('Your account is inactive.')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def permission_required(*perm_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Authentication required'}, status=401)
                return None
            profile = getattr(request.user, 'analyst_profile', None)
            if not profile or not profile.is_active:
                if _is_ajax(request):
                    return JsonResponse({'error': 'Account inactive'}, status=403)
                raise PermissionDenied('Your account is inactive.')
            for perm in perm_names:
                if not profile.has_permission(perm):
                    if _is_ajax(request):
                        return JsonResponse({'error': 'Forbidden', 'detail': f'Missing permission: {perm}'}, status=403)
                    raise PermissionDenied(f'Missing permission: {perm}')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def role_has_dashboard_access(role, dashboard):
    access_map = {
        'l1': ['L1', 'L2', 'L3', 'SOC_MGR', 'ADMIN'],
        'l2': ['L2', 'L3', 'SOC_MGR', 'ADMIN'],
        'l3': ['L3', 'SOC_MGR', 'ADMIN'],
        'manager': ['SOC_MGR', 'ADMIN'],
        'monitor': ['MONITOR', 'SOC_MGR', 'ADMIN'],
    }
    return role in access_map.get(dashboard, [])
