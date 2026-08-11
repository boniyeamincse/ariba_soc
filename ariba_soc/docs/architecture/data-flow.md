# Data Flow Diagrams

## Alert Ingestion Flow

```
Wazuh Agent (on monitored host)
  │
  ├── Collects logs, events, file integrity data
  │
  ▼
Wazuh Manager (10.24.66.2:55000)
  │
  ├── Processes rules, generates alerts
  │
  ▼
Wazuh Indexer (10.24.66.2:9200)
  │
  ├── Indexes alerts in OpenSearch (wazuh-alerts-YYYY.MM.DD)
  │
  ▼
┌─────────────────────────────────────┐
│      Django Sync Engine             │
│                                     │
│   ┌──────────────┐  ┌────────────┐ │
│   │ManagerClient │  │IndexerClient│ │
│   │(JWT, REST)   │  │(Basic Auth) │ │
│   └──────┬───────┘  └─────┬──────┘ │
│          │                │        │
│   ┌──────┴────────────────┴──────┐ │
│   │   fetch_wazuh_alerts()       │ │
│   │   - authenticate()           │ │
│   │   - get_alerts(since)        │ │
│   │   - dedup by wazuh_alert_id  │ │
│   │   - create Alert records     │ │
│   │   - log to WazuhSyncLog      │ │
│   └──────────────────────────────┘ │
└─────────────────────────────────────┘
  │
  ▼
PostgreSQL Database
  ├── alerts_alert (alert records)
  ├── alerts_alertauditlog (change history)
  └── wazuh_integration_wazuhsynclog (sync history)
```

## User Request Flow

```
Browser (HTTPS)
  │
  ├── Request to https://ariba-soc.example.com/alerts/table/
  │
  ▼
Nginx (port 443)
  │
  ├── SSL termination
  ├── Serve static files from /static/
  └── Proxy remaining requests to Gunicorn
  │
  ▼
Gunicorn (port 8091)
  │
  ├── WSGI handler
  │
  ▼
Django Middleware Stack
  ├── SecurityMiddleware
  ├── SessionMiddleware
  ├── CommonMiddleware
  ├── CsrfViewMiddleware
  ├── AuthMiddleware
  ├── MessageMiddleware
  ├── AuditMiddleware (logs request)
  │
  ▼
URL Router (config/urls.py)
  │
  ├── Match → alerts.urls
  │
  ▼
alerts.views.alert_table
  │
  ├── @login_required (check auth)
  ├── @role_required (check role)
  ├── Query alerts with filters
  │
  ▼
Template: templates/ariba_soc/alert_table.html
  │
  ├── Extends base.html
  ├── Role-gated navigation
  ├── Alert table with pagination
  │
  ▼
HTML response → Browser renders page
```

## AJAX Assignment Flow

```
Analyst clicks "Assign" on alert detail page
  │
  ▼
JavaScript: POST /alerts/<id>/assign/
  │
  ├── Data: {user_id: 123, note: "Please investigate"}
  ├── CSRF token in header
  │
  ▼
Django: alerts.views.assign_ajax
  │
  ├── @login_required
  ├── @role_required('manager', 'l2_analyst', 'admin')
  │
  ├── Update alert.assigned_to
  ├── Create AlertAuditLog (action='assignment')
  ├── Create Notification for assignee
  ├── Send email if configured
  │
  ▼
Response: {"success": true}
  │
  ▼
JavaScript: Reload page / show notification
```

## Alert Sync Decision Flow (Dedup)

```
fetch_wazuh_alerts() called
  │
  ├── last_sync = latest WazuhSyncLog completed_at
  │
  ├── ManagerClient.authenticate()
  │     └── POST /security/user/authenticate → JWT token
  │
  ├── ManagerClient.get_alerts(since=last_sync, limit=500)
  │     └── Parse response JSON
  │
  ▼
For each alert in response:
  │
  ├── wazuh_alert_id exists in DB?
  │   ├── Yes → increment alerts_skipped
  │   └── No  → create Alert object
  │               ├── Parse severity from rule.level
  │               ├── Parse title/description
  │               ├── Set status = 'new'
  │               └── increment alerts_created
  │
  ▼
After all alerts processed:
  │
  ├── Update or create WazuhSyncLog record
  │   ├── status = 'success'
  │   ├── alerts_fetched = total
  │   ├── alerts_created = new count
  │   └── alerts_skipped = dup count
  │
  ▼
Return sync result to UI
```

## Report Generation Flow

```
Manager requests report
  │
  ▼
GET /reports/alerts/?format=pdf&severity=high&from=2026-01-01
  │
  ▼
reports.views.generate_report
  │
  ├── @login_required
  ├── @role_required('manager', 'admin')
  │
  ├── Query alerts with filters
  │
  ├── If format=pdf:
  │     ├── Render HTML template with alert data
  │     ├── WeasyPrint converts HTML to PDF
  │     └── Return PDF file (Content-Type: application/pdf)
  │
  └── If format=csv:
        ├── Write CSV header row
        ├── Write alert rows
        └── Return CSV file (Content-Type: text/csv)
```
