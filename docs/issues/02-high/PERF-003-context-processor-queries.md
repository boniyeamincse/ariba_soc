# PERF-003: Context processor runs 4+ queries per page

**Severity:** High  
**Priority:** P1  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/alerts/context_processors.py`

## Current Problem
Every page load triggers 4 DB queries for alert counts + 3 queries for settings. For heavy traffic, this adds significant DB load.

## Expected Behavior
Cache counts in Redis with 30-second TTL.

## Affected Files
- `ariba_soc/alerts/context_processors.py` (lines 12-29)

## Suggested Fix
```python
from django.core.cache import cache

def user_alerts_context(request):
    if not request.user.is_authenticated:
        return {}
    
    cache_key = f'user_alerts_{request.user.id}'
    data = cache.get(cache_key)
    if data is None:
        data = {
            'my_assigned_count': Alert.objects.filter(assignee=request.user, status='In Progress').count(),
            'new_alerts_count': Alert.objects.filter(status='New').count(),
            'critical_alerts_count': Alert.objects.filter(severity='Critical').exclude(status='Closed').count(),
            'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False).count(),
        }
        cache.set(cache_key, data, 30)
    return data
```

## QA Verification
- Check Redis for cached context data
- Page load time reduced by ~50%
