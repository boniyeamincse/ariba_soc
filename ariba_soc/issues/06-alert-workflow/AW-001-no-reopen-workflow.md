# AW-001: No Reopen Workflow for Closed/Archived Alerts

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Alert Workflow

## Current Problem
Once an alert is closed (`status='Closed'`) or archived (`status='Archived'`), there is no view or action to reopen it. The `alert_edit` view (`alerts/views.py:142-154`) only updates via the `AlertEditForm`, which includes `status` in its fields (`alerts/forms.py:14`) — so technically a user could set a closed alert back to "New" via the edit form. However:
- There's no dedicated "Reopen" button or confirmation dialog
- The `alert_archive` view (`alerts/views.py:232-240`) sets `status='Archived'` with no way to undo
- No audit log action exists for "Reopened" — the `AlertAuditLog.ACTIONS` tuple includes 'Reopened' but it's never used

## Expected Behavior
A `reopen` action should be available for closed/archived alerts that:
1. Sets status back to "New"
2. Clears `closed_at` and `archived_at` timestamps
3. Creates an audit log entry with action "Reopened"
4. Shows a confirmation dialog before proceeding

## Affected Files
- `alerts/views.py` (needs `alert_reopen` view)
- `alerts/urls.py` (needs reopen route)
- `templates/ariba_soc/alert_detail.html` (needs reopen button)

## Suggested Fix
```python
@login_required
@require_POST
def alert_reopen(request, alert_id):
    alert = get_object_or_404(Alert, id=alert_id)
    if alert.status not in ('Closed', 'Archived'):
        messages.error(request, 'Only closed or archived alerts can be reopened.')
        return redirect('alerts:detail', alert_id=alert_id)
    alert.status = 'New'
    alert.closed_at = None
    alert.archived_at = None
    alert.closure_reason = ''
    alert.save()
    create_audit_log(alert, request.user, 'Reopened', 'Closed/Archived', 'New', request)
    messages.success(request, 'Alert reopened.')
    return redirect('alerts:detail', alert_id=alert_id)
```

## QA Verification
1. Close an alert → verify the detail page shows a "Reopen" button.
2. Click Reopen → alert status must become "New", `closed_at` must be null.
3. Audit log must show "Reopened" action.
