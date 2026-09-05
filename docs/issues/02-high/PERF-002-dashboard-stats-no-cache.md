# PERF-002: Dashboard stats queries not cached

**Severity:** High  
**Priority:** P1  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/dashboard/views.py`

## Current Problem
`dashboard_stats_api` runs 7 expensive aggregate queries on every request with zero caching. For a SOC with millions of alerts, this is extremely slow.

## Expected Behavior
Dashboard stats cached for 60 seconds to reduce DB load.

## Affected Files
- `ariba_soc/dashboard/views.py` (lines 34-63)

## Suggested Fix
```python
from django.views.decorators.cache import cache_page

@cache_page(60)
@login_required
def dashboard_stats_api(request):
    # ... existing code
```

## QA Verification
- First request: ~500ms
- Subsequent requests within 60s: <50ms
- Check Redis for cached data
