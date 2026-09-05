# SEC-004: No rate limiting on API endpoints

**Severity:** High  
**Priority:** P1  
**Category:** Security (DoS)  
**Status:** Open  
**File:** `ariba_soc/alerts/views.py`

## Current Problem
JSON API endpoints (`alerts_api`, `dashboard_stats_api`, `alert_move_api`) have no rate limiting. A stolen session can hammer these endpoints causing CPU exhaustion.

## Expected Behavior
- API endpoints rate limited to 100 requests/minute
- Dashboard stats cached for 60 seconds

## Affected Files
- `ariba_soc/alerts/views.py` (lines 308-395)
- `ariba_soc/dashboard/views.py` (lines 34-63)

## Suggested Fix
```python
from django.views.decorators.cache import cache_page

@cache_page(60)  # Cache for 60 seconds
@login_required
def dashboard_stats_api(request):
    # ... existing code
```

Or use `django-ratelimit`:
```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/m', method='GET')
@login_required
def alerts_api(request):
    # ...
```

## QA Verification
- Hit `/api/alerts/` 100 times in 1 minute → 101st returns 429
- Dashboard stats load in <100ms (cached)
