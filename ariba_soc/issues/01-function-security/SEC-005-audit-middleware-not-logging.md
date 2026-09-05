# SEC-005: AuditMiddleware Registered but Performs No Logging

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Function & Security

## Current Problem
`audit/middleware.py` is registered in `config/settings.py:36` but the `__call__` method is a no-op:
```python
class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response  # No logging occurs
```
The middleware imports `timezone` but never uses it. Meanwhile, `audit/models.py` defines a full `AuditLog` model with structured actions (LOGIN, LOGOUT, ALERT_CREATED, etc.) that is never written to.

## Expected Behavior
The middleware should log every request to authenticated endpoints, recording the user, action, IP, user-agent, and timestamp into `AuditLog`.

## Affected Files
- `audit/middleware.py` (entire file)
- `config/settings.py:36`

## Suggested Fix
```python
from django.utils import timezone
from .models import AuditLog

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            path = request.path_info
            # Skip logging static/media/debug
            if not path.startswith(('/static/', '/media/', '/admin/jsi18n/')):
                AuditLog.objects.create(
                    user=request.user,
                    action=self._map_action(request),
                    object_type='Page',
                    object_id=path,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
        return response

    def _map_action(self, request):
        if request.path_info == '/accounts/login/':
            return 'LOGIN'
        if request.path_info == '/accounts/logout/':
            return 'LOGOUT'
        return 'ALERT_UPDATED' if '/alerts/' in request.path_info else 'PAGE_VIEW'
```

## QA Verification
1. Hit any authenticated page after fixing — a new row must appear in `AuditLog` table.
2. Verify login/logout create "LOGIN"/"LOGOUT" actions respectively.
3. Verify `/static/` paths are not logged.
