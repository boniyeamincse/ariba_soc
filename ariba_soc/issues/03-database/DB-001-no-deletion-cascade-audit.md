# DB-001: Missing CASCADE Deletions for Audit Logs and Comments

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Database

## Current Problem
Multiple models use `on_delete=models.SET_NULL` for ForeignKey relations to `User`:
- `Alert.assignee` (`alerts/models.py:73`) — `on_delete=SET_NULL`
- `Alert.assigned_by` (`alerts/models.py:74`) — `on_delete=SET_NULL`
- `AlertComment.user` (`alerts/models.py:192`) — `on_delete=SET_NULL`
- `AlertAuditLog.user` (`alerts/models.py:219`) — `on_delete=SET_NULL`
- `NotificationSetting.recipient_user` (`settings_manager/models.py:143`) — `on_delete=SET_NULL`

While `SET_NULL` is appropriate for some fields (keeping audit history when a user is deleted), the problem is that **no migration or signal handles cleanup** of orphaned audit logs and comments. When a user is deleted:
- `Alert` records lose their assignee reference (acceptable)
- `AlertAuditLog` records lose their user reference but remain (acceptable)
- No cascade occurs on `Alert` deletion: deleting an alert does NOT cascade to `AlertComment` or `AlertAuditLog` (the FK is on the child side, and the default cascade behavior from the parent deletion should work — but only if migration defines `on_delete=CASCADE` on the alert FK, which it already does `alerts/models.py:191,218`)

The real issue: `AlertComment.alert` and `AlertAuditLog.alert` use `on_delete=CASCADE`, so deleting an alert deletes comments and logs. But there's no `on_delete=CASCADE` for `AuditLog.user` or `SettingAuditLog.user`.

## Expected Behavior
When a User is deleted, their audit trail should either:
1. Be preserved with `SET_NULL` (current behavior — fine), OR
2. Be cascaded deleted if the audit is non-essential

The current mix is OK for user deletion. The issue is that no explicit migration defines what happens to `SettingAuditLog` on user delete — it uses Django's default.

## Affected Files
- `alerts/models.py:73-74,192,219` (SET_NULL on User FK)
- `settings_manager/models.py:6-14` (SettingAuditLog.user — implicit ON_DELETE)
- `audit/middleware.py` (AuditLog model exists but middleware never writes)

## Suggested Fix
No change needed for user FK behavior (SET_NULL is correct for audit preservation). But a **database maintenance command** should be created to periodically clean up orphaned audit logs older than the retention period (from `AuditLogSetting.retention_days`).

## QA Verification
1. Delete a user who has assigned alerts — alerts must remain with `assignee=NULL`.
2. Verify no database integrity errors occur during user deletion.
