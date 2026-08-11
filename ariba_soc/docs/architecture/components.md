# Component Architecture

## Django App Dependencies

```
accounts
  ├── No internal dependencies (only Django auth)
  └── Used by: alerts, audit, dashboard, reports, wazuh_integration

alerts
  ├── Depends on: accounts (AnalystProfile for role checks)
  ├── Models: Alert, AlertComment, AlertAuditLog, Notification, AlertSource
  └── Used by: dashboard (query alerts), reports (generate from alerts)

audit
  ├── Depends on: accounts (user FK in AuditLog)
  ├── Middleware: AuditMiddleware (logs all requests)
  └── Used by: all apps (via middleware)

dashboard
  ├── Depends on: alerts (alert aggregates)
  └── No dependents

reports
  ├── Depends on: alerts (alert data), accounts (analyst data)
  ├── Uses: WeasyPrint (PDF), streaming (CSV)
  └── No dependents

settings_manager
  ├── No internal dependencies
  ├── Models: SystemSetting, SettingAuditLog
  └── Used by: all apps (via get_setting() utility)

wazuh_integration
  ├── Depends on: accounts (role checks), alerts (Alert model creation)
  ├── Models: WazuhManagerConfig, WazuhConfiguration, WazuhSyncLog
  └── No dependents
```

## Component Interaction Map

```
wazuh_integration
  │
  ├── services.ManagerClient ──→ Wazuh Manager API (external)
  ├── services.IndexerClient ──→ Wazuh Indexer API (external)
  │
  └── services.fetch_wazuh_alerts()
        │
        ├── queries alerts_alert (dedup check)
        ├── creates alerts_alert records
        ├── creates wazuh_integration_wazuhsynclog
        └── logs to alerts_alertauditlog via alerts.models

alerts
  │
  ├── views.alert_table ──→ renders alert_table.html
  ├── views.alert_board ──→ renders alert_board.html (kanban)
  ├── views.my_alerts ──→ renders alert_table.html (filtered)
  ├── views.alert_detail ──→ renders alert_detail.html
  ├── views.edit_alert_ajax ──→ JSON response
  ├── views.assign_ajax ──→ JSON response + Notification + email
  │
  └── models.Alert ──→ used by dashboard, reports

dashboard
  │
  ├── views.dashboard_home ──→ renders dashboard.html
  ├── views.severity_breakdown ──→ JSON response
  ├── views.daily_trend ──→ JSON response
  └── views.status_distribution ──→ JSON response

reports
  │
  ├── views.generate_report ──→ PDF/CSV download
  └── views.analyst_performance_report ──→ PDF/CSV download

config.urls
  │
  ├── /accounts/ → accounts.urls
  ├── /alerts/   → alerts.urls
  ├── /          → dashboard.urls
  ├── /reports/  → reports.urls
  ├── /settings/ → settings_manager.urls
  ├── /audit/    → audit.urls
  └── /wazuh/    → wazuh_integration.urls
```

## Service Layer (wazuh_integration)

```
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ManagerClient                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  - base_url: str                               │    │
│  │  - token: str (JWT, fetched via authenticate()) │    │
│  │                                                 │    │
│  │  + authenticate() -> str                        │    │
│  │  + get_alerts(since, limit) -> list             │    │
│  │  + get_agent_status() -> list                   │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  IndexerClient                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  - base_url: str                               │    │
│  │  - auth: (user, pass) tuple                    │    │
│  │                                                 │    │
│  │  + search(query: dict) -> dict                  │    │
│  │  + cluster_health() -> dict                     │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  fetch_wazuh_alerts()                                    │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. Orchestrates ManagerClient                   │    │
│  │  2. Dedup against Alert table                    │    │
│  │  3. Creates Alert records                        │    │
│  │  4. Logs to WazuhSyncLog                         │    │
│  │  5. Returns sync summary dict                    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Middleware Pipeline

```
Request → SecurityMiddleware → SessionMiddleware → CommonMiddleware
  → CsrfViewMiddleware → AuthMiddleware → MessageMiddleware
  → AuditMiddleware → URL Router → View
```

**AuditMiddleware** (`audit/middleware.py`):
- Intercepts every request after auth
- Records: actor, action (based on HTTP method), model name (from URL), object ID, IP address
- Excludes static files and admin media from logging

## Template Inheritance

```
base.html
  ├── Navbar (role-gated)
  ├── Messages block
  ├── Content block
  │
  ├── registration/login.html (extends base.html)
  ├── registration/logged_out.html (extends base.html)
  │
  ├── ariba_soc/dashboard.html (extends base.html)
  ├── ariba_soc/alert_table.html (extends base.html)
  ├── ariba_soc/alert_board.html (extends base.html)
  ├── ariba_soc/alert_detail.html (extends base.html)
  ├── ariba_soc/wazuh_status.html (extends base.html)
  ├── ariba_soc/settings.html (extends base.html)
  └── ariba_soc/audit_log.html (extends base.html)
```
