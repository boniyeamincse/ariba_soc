# CODE-001: AuditMiddleware is a no-op

**Severity:** Medium  
**Priority:** P2  
**Category:** Code Quality  
**Status:** Open  
**File:** `ariba_soc/audit/middleware.py`

## Current Problem
`AuditMiddleware` is in the middleware stack but performs zero audit logging. Dead code that wastes a middleware cycle per request.

## Expected Behavior
Either implement request logging or remove from middleware stack.

## Affected Files
- `ariba_soc/audit/middleware.py` (lines 1-9)
- `ariba_soc/config/settings.py` (line 68)

## Suggested Fix
```python
class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Log request if user is authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            AuditLog.objects.create(
                user=request.user,
                action=f'{request.method} {request.path}',
                ip_address=request.META.get('REMOTE_ADDR'),
                status_code=response.status_code,
            )
        
        return response
```

Or remove from `MIDDLEWARE` if not needed.

## QA Verification
- Check `audit_auditlog` table for request entries
- Or confirm middleware removed from settings
