# PERF-007: wallboard uses len() instead of count()

**Severity:** Low  
**Priority:** P3  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/monitor/services.py`

## Current Problem
`wallboard_executive()` calls `len(active_incidents(limit=1000))` which fetches up to 1000 objects just to count them.

## Expected Behavior
Use `.count()` query.

## Affected Files
- `ariba_soc/monitor/services.py` (line 273)

## Suggested Fix
```python
# Before
active = len(active_incidents(limit=1000))

# After
active = Alert.objects.filter(
    status__in=['New', 'In Progress'],
    severity__in=['Critical', 'High']
).count()
```

## QA Verification
- Wallboard loads faster
- Single COUNT query instead of SELECT 1000 rows
