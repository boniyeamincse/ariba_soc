# RP-001: CSV/Excel Exports Have No Filter or Date Range Parameters

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Reports

## Current Problem
`reports/views.py:33-44` and `reports/views.py:47-65` export ALL alerts unconditionally:
```python
for alert in Alert.objects.all().select_related('assignee')[:5000]:
```
There is no way to:
- Filter by date range (today, this week, custom)
- Filter by severity, status, or verdict
- Export only selected alerts
- Choose which columns to include

The hardcoded `[:5000]` limit means large exports silently truncate data without warning the user.

## Expected Behavior
Export endpoints should accept GET parameters for filtering, matching the same filters available on the alert table page. The user should be able to export the current filtered view, not every alert in the database.

## Affected Files
- `reports/views.py:32-65` (export_csv, export_excel)

## Suggested Fix
```python
@login_required
def export_csv(request):
    alerts = Alert.objects.select_related('assignee').all()
    
    # Apply same filters as alert_table
    severity = request.GET.get('severity')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if severity: alerts = alerts.filter(severity=severity)
    if status: alerts = alerts.filter(status=status)
    if date_from: alerts = alerts.filter(alert_time__gte=date_from)
    if date_to: alerts = alerts.filter(alert_time__lte=date_to)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ariba_alerts_export.csv"'
    # ... write filtered queryset
    return response
```

## QA Verification
1. Navigate to `/reports/export/csv/?severity=Critical&date_from=2026-01-01` → export must contain only Critical alerts.
2. Without any filters → export all alerts (respect the 5000 limit with a warning).
3. Verify the export filename includes the date range (e.g., `ariba_alerts_2026-01-01_to_2026-07-08.csv`).
