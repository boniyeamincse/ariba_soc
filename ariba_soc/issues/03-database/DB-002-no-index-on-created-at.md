# DB-002: Missing Database Indexes on Frequently Filtered Fields

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Database

## Current Problem
The `Alert` model (`alerts/models.py:130-139`) defines indexes on `status`, `severity`, `verdict`, `assignee`, `alert_time`, `rule_id`, `hostname`, `source_ip`, and `wazuh_alert_id`. However, the following models have **no indexes** on frequently filtered/sorted fields:

- `AlertComment.created_at` — sorted by in `Meta.ordering`
- `AlertAuditLog.created_at` — sorted by in `Meta.ordering`
- `SettingAuditLog.created_at` — sorted by in `Meta.ordering`
- `AuditLog.created_at` — sorted by in `Meta.ordering`
- `AlertComment.alert` — filtered by `alert.comments` frequently
- `WazuhSyncLog.started_at` — sorted/filtered in views

While Django creates implicit indexes for ForeignKey fields (`alert` FK on comments), the `created_at` ordering fields are not indexed. On large datasets (10K+ comments or audit logs), the ORDER BY will perform a full table sort.

## Expected Behavior
All `created_at` fields used in `Meta.ordering` should have an explicit index.

## Affected Files
- `alerts/models.py:197-198` (AlertComment ordering)
- `alerts/models.py:227-228` (AlertAuditLog ordering)
- `audit/models.py:31-32` (AuditLog ordering)
- `settings_manager/models.py:16-17` (SettingAuditLog ordering)

## Suggested Fix
Add indexes to each model's Meta:
```python
class AlertComment(models.Model):
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['alert', 'created_at']),
        ]
```
Generate and apply: `python manage.py makemigrations && python manage.py migrate`

## QA Verification
1. Run `EXPLAIN ANALYZE SELECT * FROM alerts_alertcomment ORDER BY created_at;` before and after — the post-index query must show an Index Scan instead of Seq Scan.
2. Verify migration runs without errors.
