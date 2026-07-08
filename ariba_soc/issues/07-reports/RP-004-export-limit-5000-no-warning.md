# RP-004: Export Limits to 5000 Rows Silently

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: Reports

## Current Problem
`reports/views.py:38` exports a maximum of 5000 alerts:
```python
for alert in Alert.objects.all().select_related('assignee')[:5000]:
```
If the database has more than 5000 alerts, the remaining rows are silently dropped. The user receives a complete-looking file with no indication that data was truncated.

## Expected Behavior
When the export exceeds the limit:
- Option A: Stream the full dataset (no limit, use server-side streaming)
- Option B: Show a warning banner: "Export limited to 5000 alerts. Use filters to narrow results."
- Option C: Paginate the export with multiple files

## Affected Files
- `reports/views.py:38` (CSV export limit)
- `reports/views.py:56` (Excel export limit)

## Suggested Fix
Add a count check:
```python
total = Alert.objects.count()
if total > 5000:
    messages.warning(request, f'Export limited to 5000 of {total} alerts. Apply date filters to narrow results.')
alerts = Alert.objects.all().select_related('assignee')[:5000]
```

## QA Verification
1. Have 6000 alerts in the database.
2. Export CSV → must show a warning banner about the 5000 limit.
3. Apply a date filter that returns <5000 alerts → no warning.
