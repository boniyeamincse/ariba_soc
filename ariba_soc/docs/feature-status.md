# Feature Status

Legend: ✅ Complete | 🔄 In Progress | ❌ Not Started | 🚫 Removed

## Core Platform

| Feature | Status | Notes |
|---------|--------|-------|
| Django project scaffolding | ✅ | config/ package |
| PostgreSQL + SQLite support | ✅ | Dual DB config |
| Glassmorphism CSS theme | ✅ | 700+ rules in ariba-soc.css |
| Bootstrap 5 responsive base | ✅ | base.html + all templates |
| Environment variable config | ✅ | python-decouple |
| CI pipeline (GitHub Actions) | ✅ | 19 tests, PostgreSQL 15 |
| Docker deployment | ✅ | Dockerfile + docker-compose.yml |
| systemd service | ✅ | ariba-soc.service |

## Authentication & Authorization

| Feature | Status | Notes |
|---------|--------|-------|
| Login/logout | ✅ | Django auth + custom decorators |
| Role-based access (4 tiers) | ✅ | Admin, Manager, L2, L1 |
| `@role_required` decorator | ✅ | Per-view permission checks |
| Template-level role checks | ✅ | Nav items gated by user role |
| User profile (AnalystProfile) | ✅ | Extended user model with role |
| Superuser auto Admin | ✅ | Via signal |

## Wazuh Integration

| Feature | Status | Notes |
|---------|--------|-------|
| WazuhManagerConfig model | ✅ | Manager API credentials |
| WazuhConfiguration model (Indexer) | ✅ | Indexer OpenSearch credentials |
| ManagerClient service | ✅ | JWT auth, REST API calls |
| IndexerClient service | ✅ | Basic auth, OpenSearch queries |
| Test connection endpoints | ✅ | Both Manager + Indexer |
| Manual force sync | ✅ | Dedup, pagination, audit logging |
| Scheduled sync | ✅ | Via WazuhSyncLog tracking |
| Migration 0003 (dual-arch) | ✅ | Removed single api_type |

## Alert Management

| Feature | Status | Notes |
|---------|--------|-------|
| Alert model | ✅ | Full lifecycle tracking |
| Severity levels | ✅ | critical, high, medium, low, info |
| Status workflow | ✅ | 6 statuses: new→acknowledged→in_progress→resolved/closed/escalated |
| Dedup on sync | ✅ | Matches by wazuh_alert_id |
| Alert sources tracking | ✅ | AlertSource model + direct field |
| Alert comments | ✅ | AlertComment model |
| Alert audit log | ✅ | AlertAuditLog model |
| Table view with filters | ✅ | Severity, status, date range, search |
| Kanban board view | ✅ | Drag-and-drop columns per status |
| My Alerts view | ✅ | Filtered to current user |
| AJAX edit/assign | ✅ | Inline without page reload |
| Notification on assign | ✅ | In-app + email |

## Dashboard

| Feature | Status | Notes |
|---------|--------|-------|
| Stats cards | ✅ | Total alerts, critical, by status |
| Severity breakdown chart | ✅ | Bar chart data API |
| Daily trend chart | ✅ | Line chart data API |
| Status distribution | ✅ | Pie chart data API |
| Recent alerts list | ✅ | Last 10 alerts |
| Top analyst performance | ✅ | By resolved/closed count |

## Reporting

| Feature | Status | Notes |
|---------|--------|-------|
| PDF report generation | ✅ | WeasyPrint-based |
| CSV export | ✅ | Streaming CSV |
| Alert report with filters | ✅ | Date range, severity, analyst |
| Analyst performance report | ✅ | Resolved/closed metrics |

## Audit

| Feature | Status | Notes |
|---------|--------|-------|
| Request audit middleware | ✅ | Logs all requests |
| AuditLog model | ✅ | Generic audit trail |
| AlertAuditLog model | ✅ | Alert-specific audit trail |
| Settings audit log | ✅ | SettingAuditLog model |
| Audit log viewer | ✅ | Filterable admin view |

## Settings Manager

| Feature | Status | Notes |
|---------|--------|-------|
| SystemSetting model | ✅ | Key-value store |
| Categorization | ✅ | General, Alerts, Wazuh, SLA, Escalation |
| Data type support | ✅ | str, int, bool, json, float |
| Setting audit trail | ✅ | SettingAuditLog |
| Settings UI | ✅ | Admin panel |

## Deployment

| Feature | Status | Notes |
|---------|--------|-------|
| Nginx reverse proxy config | ✅ | deploy/nginx.conf |
| Gunicorn service file | ✅ | deploy/ariba-soc.service |
| Dockerfile | ✅ | Multi-stage build |
| docker-compose.yml | ✅ | App + PostgreSQL |
| SSL/TLS support | ✅ | Via Nginx certs |
