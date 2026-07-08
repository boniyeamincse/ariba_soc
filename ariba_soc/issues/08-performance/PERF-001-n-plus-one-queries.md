# PERF-001: N+1 Query Patterns in Multiple Views

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Performance

## Current Problem
Several views and templates trigger N+1 query patterns:

1. **Alert Board** (`alerts/views.py:81-127`): Filters the queryset 8 separate times (new, in_progress, awaiting, pending, escalated, closed, archived, true_positives, false_positives). Each `.filter()` triggers a separate DB query. For large datasets, this results in 9 queries instead of 1.

2. **User Management** (`settings_manager/views.py:57`): Uses `select_related('analyst_profile')` ✓ (good), but the template at `user_management.html:47` accesses `u.analyst_profile.role` and `u.analyst_profile.get_role_display()` which call `get_role_display()` — this triggers a method call per row but no extra query. However, `u.get_full_name` and `u.email` are direct User fields, so this is fine.

3. **Alert Detail** (`alerts/views.py:131-138`): Uses `select_related('assignee', 'source', 'assigned_by')` ✓. Comments use `.select_related('user')` ✓. Audit logs use `.select_related('user')` ✓. This one is correct.

4. **Settings Dashboard** (`settings_manager/views.py:39-50`): Counts 7 different models with separate queries. Could be optimized to run in parallel or use cached counts.

5. **Role Permission** (`settings_manager/views.py:159`): The template loops over `role_choices` and for each loops over `roles`. With 6 roles, this is only 36 iterations — acceptable. But the nested `{% for %}` loops can be simplified.

## Expected Behavior
Query counts should be minimized:
- Alert board: single query with aggregation
- Settings dashboards: cache counts or use single aggregation query
- All list views should have O(1) queries per page load

## Affected Files
- `alerts/views.py:81-127` (alert_board)
- `settings_manager/views.py:39-50` (settings_dashboard)
- `settings_manager/views.py:129-159` (role_permission — template nesting)

## Suggested Fix
Optimize alert_board:
```python
from django.db.models import Count, Q

all_alerts = Alert.objects.select_related('assignee', 'source').filter(
    alert_time__year=year, alert_time__month=month
)
# Single pass grouping
status_groups = {
    'new': all_alerts.filter(status='New'),
    'in_progress': all_alerts.filter(status='In Progress'),
    ...
}
```
Better yet, use annotation:
```python
status_counts = all_alerts.values('status').annotate(count=Count('id'))
verdict_counts = all_alerts.filter(status='Closed').values('verdict').annotate(count=Count('id'))
```

## QA Verification
1. Enable Django Debug Toolbar (`DEBUG_TOOLBAR=True` in settings).
2. Load Alert Board → verify < 10 queries (currently ~12-15).
3. Load Settings Dashboard → verify < 10 queries (currently ~8-10).
4. Apply `select_related` and `prefetch_related` until query counts are minimized.
