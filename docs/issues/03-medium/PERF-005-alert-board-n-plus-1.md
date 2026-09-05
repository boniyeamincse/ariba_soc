# PERF-005: alert_board view runs 8+ separate queries

**Severity:** Medium  
**Priority:** P2  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/alerts/views.py`

## Current Problem
`alert_board` creates the same filtered queryset 8 times (one per status column), each executing a separate SQL query.

## Expected Behavior
Single query with conditional aggregation.

## Affected Files
- `ariba_soc/alerts/views.py` (lines 119-129)

## Suggested Fix
```python
from django.db.models import Count, Case, When, IntegerField

def alert_board(request):
    base_qs = Alert.objects.all()
    
    # Single query for all status counts
    status_counts = base_qs.aggregate(
        new_count=Count('id', filter=Q(status='New')),
        in_progress_count=Count('id', filter=Q(status='In Progress')),
        # ... etc
    )
    
    # Or fetch all and group in Python
    all_alerts = base_qs.select_related('assignee').order_by('-created_at')
    columns = {}
    for alert in all_alerts:
        columns.setdefault(alert.status, []).append(alert)
```

## QA Verification
- Check query count: should be 1-2 instead of 8+
- Board loads in <200ms
