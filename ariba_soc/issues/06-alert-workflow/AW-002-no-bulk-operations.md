# AW-002: No Bulk Select / Bulk Operations on Alert Table

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Alert Workflow

## Current Problem
The alert table (`alerts/views.py:17-77` and `templates/ariba_soc/alert_table.html`) only supports single-item actions: click an alert to view detail, then edit/assign/close from the detail page. There is no:
- Checkbox column to select multiple alerts
- Bulk assign dropdown
- Bulk status/severity/verdict change
- Bulk archive or close
- "Select all" / "Select none" controls

SOC analysts frequently need to process multiple alerts at once (e.g., close 10 false positives, assign 5 alerts to a colleague). Single-item processing creates significant overhead.

## Expected Behavior
The alert table should have a checkbox column with:
- A master checkbox in the header (select all / deselect all)
- A floating action bar that appears when ≥1 alert is selected
- Bulk actions: Assign, Change Status, Change Verdict, Close, Archive
- Confirmation dialog for destructive actions

## Affected Files
- `templates/ariba_soc/alert_table.html` (checkbox column + action bar)
- `alerts/views.py` (needs bulk action endpoint)
- `alerts/urls.py` (needs bulk route)
- `static/js/ariba-soc.js` (selection logic)

## Suggested Fix
Add endpoint:
```python
@login_required
@require_POST
def alert_bulk_action(request):
    alert_ids = request.POST.getlist('alert_ids')
    action = request.POST.get('action')
    value = request.POST.get('value')
    alerts = Alert.objects.filter(id__in=alert_ids)
    count = alerts.count()
    # Apply action based on type
    ...
    messages.success(request, f'{count} alerts updated.')
    return redirect('alerts:table')
```

## QA Verification
1. Select 3 alerts on the table → action bar must appear with count.
2. Choose "Close" with verdict "False Positive" → all 3 must close.
3. Verify audit logs show each operation individually.
