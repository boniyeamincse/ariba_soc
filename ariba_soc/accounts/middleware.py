from django.shortcuts import redirect

# Paths a MONITOR-role account may reach directly. Everything else redirects
# to the dashboard -- this is the real access control; nav-link hiding in
# base.html is cosmetic on top of this, not a substitute for it.
MONITOR_ALLOWED_PREFIXES = (
    '/dashboard/',
    '/accounts/',
    '/static/',
    '/media/',
)


class MonitorAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            profile = getattr(user, 'analyst_profile', None)
            if profile and profile.role == 'MONITOR' and not request.path.startswith(MONITOR_ALLOWED_PREFIXES):
                return redirect('dashboard:home')
        return self.get_response(request)
