# PERF-006: reports _rows() runs 10 separate count queries

**Severity:** Medium  
**Priority:** P2  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/reports/services.py`

## Current Problem
`_rows()` runs 10 separate `.count()` queries for each metric. Could be consolidated into a single annotated query.

## Expected Behavior
Single query with conditional aggregation.

## Affected Files
- `ariba_soc/reports/services.py` (lines 72-85)

## Suggested Fix
```python
from django.db.models import Count, Q

def _rows(qs, alert_type):
    metrics = qs.aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(severity='Critical')),
        high=Count('id', filter=Q(severity='High')),
        medium=Count('id', filter=Q(severity='Medium')),
        low=Count('id', filter=Q(severity='Low')),
        informational=Count('id', filter=Q(severity='Informational')),
        new=Count('id', filter=Q(status='New')),
        in_progress=Count('id', filter=Q(status='In Progress')),
        closed=Count('id', filter=Q(status='Closed')),
        escalated=Count('id', filter=Q(is_escalated=True)),
    )
    return [alert_type, metrics['total'], metrics['critical'], ...]
```

## QA Verification
- Check query count: 1 instead of 10
- Report generation 2x faster
