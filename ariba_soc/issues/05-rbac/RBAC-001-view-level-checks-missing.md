# RBAC-001: Missing Permission Checks on Alert Views

- **Severity**: Critical
- **Priority**: P0 (immediate)
- **Category**: RBAC

## Current Problem
The `RolePermission` model (`accounts/models.py:43-76`) defines 16 boolean permission fields (`can_view_alerts`, `can_assign_self`, `can_change_status`, etc.), but **no view in `alerts/views.py` actually checks these permissions**. Every view only requires `@login_required`.

For example:
- `alert_escalate` (`alerts/views.py:187-204`) — any authenticated user can escalate, even if `can_escalate_alert` is False
- `alert_close` (`alerts/views.py:207-229`) — any user can close alerts, even VIEWER role
- `alert_archive` (`alerts/views.py:232-240`) — no archive permission check
- `alert_edit` (`alerts/views.py:142-154`) — can change severity/status without `can_change_severity` or `can_change_status`

The RBAC system is defined but never enforced.

## Expected Behavior
Each view or action should check the user's role permissions before allowing the operation. Users without the required permission should receive a 403 or error message.

## Affected Files
- `alerts/views.py:142-154` (alert_edit — needs can_change_status/severity/verdict checks)
- `alerts/views.py:157-167` (alert_assign — needs can_assign_self / can_assign_others)
- `alerts/views.py:186-204` (alert_escalate — needs can_escalate_alert)
- `alerts/views.py:207-229` (alert_close — needs can_close_alert)
- `alerts/views.py:232-240` (alert_archive — needs can_archive)

## Suggested Fix
Add a helper function:
```python
def check_perm(user, perm):
    profile = getattr(user, 'analyst_profile', None)
    if not profile or not profile.has_permission(perm):
        raise PermissionDenied(f"You don't have permission: {perm}")
```

Then in each view:
```python
def alert_close(request, alert_id):
    check_perm(request.user, 'can_close_alert')
    ...
```

## QA Verification
1. Log in as VIEWER, try to close an alert → must receive 403 error.
2. Log in as L1 analyst, try to change severity → must fail (L1 default: can_change_severity=False).
3. Log in as SOC Manager, try the same operations → must succeed.
