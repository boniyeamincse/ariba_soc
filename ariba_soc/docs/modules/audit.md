# Audit Module

## Purpose

Provides comprehensive audit logging for compliance and troubleshooting.

## Key Model: `AuditLog`

| Field | Type | Description |
|-------|------|-------------|
| actor | FK → User (nullable) | Who performed the action |
| action | CharField(50) | CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc. |
| model_name | CharField(100) | Model affected |
| object_id | CharField(100) | Object primary key |
| details | JSONField | Change details |
| ip_address | GenericIPAddressField | Request origin IP |
| timestamp | DateTimeField | Auto-set on creation |

## Middleware: `AuditMiddleware`

Registered last in MIDDLEWARE stack. Intercepts every request and records:
- LOGIN/LOGOUT on auth views
- CREATE on POST requests
- UPDATE on POST/PUT requests
- DELETE on DELETE requests

Excludes static files, media, and certain paths from logging.

## View: `audit_log_view`

Admin-only page displaying the audit log in a filterable table:
- Filter by action, model, actor, date range
- Paginated results
- Read-only (no delete/edit)

## Dependencies

- **accounts:** User FK
- No dependents (used passively via middleware)
