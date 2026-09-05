# CODE-002: DRY violation in settings_manager views

**Severity:** Medium  
**Priority:** P2  
**Category:** Code Quality  
**Status:** Open  
**File:** `ariba_soc/settings_manager/views.py`

## Current Problem
Every view repeats the same access-check pattern 30+ times:
```python
if not _check_settings_access(request.user):
    messages.error(request, 'Access denied.')
    return redirect('alerts:table')
```

## Expected Behavior
Single decorator handles access check.

## Affected Files
- `ariba_soc/settings_manager/views.py` (all views)

## Suggested Fix
```python
from functools import wraps

def settings_access_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not _check_settings_access(request.user):
            messages.error(request, 'Access denied.')
            return redirect('alerts:table')
        return view_func(request, *args, **kwargs)
    return wrapper

# Usage
@settings_access_required
def settings_dashboard(request):
    # ... no access check needed
```

## QA Verification
- All settings views still require auth + role
- Code reduced by 100+ lines
