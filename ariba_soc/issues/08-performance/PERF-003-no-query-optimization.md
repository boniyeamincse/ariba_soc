# PERF-003: Missing select_related / prefetch_related on Related Fields

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Performance

## Current Problem
While the main `alert_table` view uses `select_related('assignee', 'source')` correctly, several other views and templates do not:

1. **`my_alerts`** (`alerts/views.py:245`): `Alert.objects.filter(assignee=request.user).select_related('source')` — missing `.select_related('assignee')` (can't select_related itself, but could use `select_related('source')` which is there ✓). Actually this is fine.

2. **`alert_board`** (`alerts/views.py:82`): `Alert.objects.select_related('assignee', 'source').all()` ✓

3. **`wazuh_status`** (`wazuh_integration/views.py:23`): `WazuhSyncLog.objects.all()[:20]` — no `select_related()` but there are no FK fields on WazuhSyncLog. Fine.

4. **`export_csv` / `export_excel`** (`reports/views.py:38,56`): `Alert.objects.all().select_related('assignee')` — correct, but for 5000 rows this is heavy. Missing `only()` or `values()` to select only needed columns.

5. **`alerts_api`** (`alerts/views.py:256`): `Alert.objects.select_related('assignee').all().order_by('-alert_time')[:100]` — loads ALL columns but only uses 12 fields. Should use `.only()` or `.values()`.

## Expected Behavior
Queries should only fetch the columns they need using `.only()` or `.values()`. The Wazuh agent fetch should timeout properly.

## Affected Files
- `alerts/views.py:256` (alerts_api — loads entire model)
- `reports/views.py:38,56` (exports — loads entire model)
- `wazuh_integration/views.py:23` (status query)

## Suggested Fix
```python
def alerts_api(request):
    alerts = Alert.objects.select_related('assignee').only(
        'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
        'assignee_id', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status'
    ).order_by('-alert_time')[:100]
    ...
```
Use `.values()` for simpler serialization:
```python
data = list(Alert.objects.values(
    'id', 'alert_name', 'severity', 'status', 'verdict', 'priority',
    'assignee__username', 'source_name', 'hostname', 'alert_time', 'rule_id', 'sla_status'
).order_by('-alert_time')[:100])
```

## QA Verification
1. Load the alert API endpoint — the SQL query must show a specific column list, not `SELECT *`.
2. Use `connection.queries` to verify only needed columns are fetched.
3. The response must still contain all required fields.
