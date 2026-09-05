from django.shortcuts import redirect
from django.urls import reverse

MONITOR_ALLOWED_PREFIXES = (
    '/dashboard/',
    '/monitor/',
    '/accounts/',
    '/static/',
    '/media/',
)

ROLE_DASHBOARD_MAP = {
    'L1': 'dashboard:l1',
    'L2': 'dashboard:l2',
    'L3': 'dashboard:l3',
    'SOC_MGR': 'dashboard:manager',
    'ADMIN': 'dashboard:manager',
    'MONITOR': 'monitor:wallboard',
    'VIEWER': 'dashboard:l1',
    'SOC_ENG': 'dashboard:l3',
}


class MonitorAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'analyst_profile', None)
            if profile and profile.role == 'MONITOR' and not request.path.startswith(MONITOR_ALLOWED_PREFIXES):
                return redirect('monitor:wallboard')
        return self.get_response(request)


class RoleBasedLoginRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


def get_role_dashboard_url(user):
    profile = getattr(user, 'analyst_profile', None)
    if not profile:
        return reverse('alerts:table')
    url_name = ROLE_DASHBOARD_MAP.get(profile.role, 'alerts:table')
    try:
        return reverse(url_name)
    except Exception:
        return reverse('alerts:table')
