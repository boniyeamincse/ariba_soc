# SEC-002: Missing @login_required on settings_manager views

**Severity:** Critical  
**Priority:** P0  
**Category:** Security (Auth Bypass)  
**Status:** Open  
**File:** `ariba_soc/settings_manager/views.py`

## Current Problem
All 30+ views in `settings_manager/views.py` lack `@login_required`. The `_check_settings_access()` function checks role but not authentication. Unauthenticated users can access settings pages.

## Expected Behavior
Every settings view requires authentication before any role check.

## Affected Files
- `ariba_soc/settings_manager/views.py` (lines 43-741, all views)
- `ariba_soc/settings_manager/urls.py`

## Suggested Fix
```python
from django.contrib.auth.decorators import login_required

@login_required
def settings_dashboard(request):
    if not _check_settings_access(request.user):
        messages.error(request, 'Access denied.')
        return redirect('alerts:table')
    # ... rest of view
```

Or create a decorator:
```python
from functools import wraps

def settings_access_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not _check_settings_access(request.user):
            messages.error(request, 'Access denied.')
            return redirect('alerts:table')
        return view_func(request, *args, **kwargs)
    return wrapper
```

## QA Verification
- Access `/settings/` without login → redirects to login
- Access `/settings/users/` without login → redirects to login
