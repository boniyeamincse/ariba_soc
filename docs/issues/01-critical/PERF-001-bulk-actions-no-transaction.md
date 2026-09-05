# PERF-001: Bulk actions not wrapped in transaction

**Severity:** Critical  
**Priority:** P0  
**Category:** Performance / Reliability  
**Status:** Open  
**File:** `ariba_soc/alerts/views.py`

## Current Problem
`alert_bulk_action` with 'close' action calls `alert.save()` individually in a loop without `transaction.atomic()`. If the process crashes mid-loop, you get partial state (some alerts closed, some not).

## Expected Behavior
Bulk operations should be atomic — all succeed or all fail.

## Affected Files
- `ariba_soc/alerts/views.py` (lines 360-368)

## Suggested Fix
```python
from django.db import transaction

@require_POST
@login_required
def alert_bulk_action(request):
    data = json.loads(request.body)
    action = data.get('action')
    ids = data.get('ids', [])
    
    with transaction.atomic():
        alerts = Alert.objects.filter(id__in=ids)
        if action == 'close':
            alerts.update(status='Closed', closed_at=timezone.now())
            for alert in alerts:
                create_audit_log(alert, request.user, 'Bulk Closed')
```

## QA Verification
- Bulk close 10 alerts → all close or none close on error
- Check audit logs for bulk operation entries
