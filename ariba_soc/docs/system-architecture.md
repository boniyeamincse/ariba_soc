# System Architecture

## High-Level Overview

```
┌────────────────────────────────────────────────────────────┐
│                        Browser                             │
│              (Glassmorphism Bootstrap 5 UI)                 │
└────────────────────┬───────────────────────────────────────┘
                     │ HTTPS :8091
                     ▼
┌────────────────────────────────────────────────────────────┐
│                   Nginx (Reverse Proxy)                     │
│              SSL termination, static files                  │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│                  Gunicorn (WSGI Server)                     │
│                     Django App                              │
├────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌───────────────┐  │
│  │accounts  │ │ alerts   │ │audit    │ │dashboard      │  │
│  │ (auth,   │ │ (models, │ │ (audit  │ │ (stats,charts)│  │
│  │  roles)  │ │  views)  │ │  trail) │ │               │  │
│  └──────────┘ └──────────┘ └─────────┘ └───────────────┘  │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌───────────────┐  │
│  │reports   │ │wazuh_    │ │settings_│ │config         │  │
│  │ (PDF/CSV)│ │integration│ │manager  │ │(settings,URLs)│  │
│  └──────────┘ └──────────┘ └─────────┘ └───────────────┘  │
└────────────────────┬───────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌─────────────────┐  ┌──────────────────────────┐
│   PostgreSQL    │  │    Wazuh Server (10.24.66.2) │
│   (Production)  │  │                            │
│   or SQLite     │  │  ┌─────────────────────┐  │
│   (Dev)         │  │  │  Manager API :55000 │  │
│                 │  │  │  (REST, JWT auth)   │  │
│                 │  │  ├─────────────────────┤  │
│                 │  │  │  Indexer API :9200  │  │
│                 │  │  │  (OpenSearch, Basic │  │
│                 │  │  │   Auth)             │  │
│                 │  │  └─────────────────────┘  │
└─────────────────┘  └──────────────────────────┘
```

## Django MVT Architecture

The app follows Django's Model-View-Template pattern:

- **Models** (`models.py` in each app): Define data structure, relationships, validation.
- **Views** (`views.py`): Handle HTTP requests, enforce permissions, query models, render templates.
- **Templates** (`templates/`): HTML with Django template language, extends `base.html`.
- **URLs** (`urls.py`): Route URL patterns to views.
- **Services** (`services.py` in `wazuh_integration`): Business logic for external API calls.
- **Forms** (`forms.py`): Django ModelForms for data input.
- **Middlewares** (`middleware.py` in `audit`): Cross-cutting concerns (audit logging).
- **Admin** (`admin.py`): Django admin configuration.

## Wazuh Dual-Connection Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Django Application                   │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │  ManagerClient   │    │     IndexerClient      │  │
│  │  (services.py)   │    │    (services.py)       │  │
│  │                  │    │                        │  │
│  │  JWT Auth        │    │  Basic Auth            │  │
│  │  REST API calls  │    │  OpenSearch SQL/DSL    │  │
│  │  /security/alerts│    │  /_search on           │  │
│  │                  │    │  wazuh-alerts-*        │  │
│  └────────┬─────────┘    └───────────┬────────────┘  │
│           │                          │               │
│  ┌────────┴──────────────────────────┴────────────┐  │
│  │         fetch_wazuh_alerts()                   │  │
│  │         (sync orchestration)                   │  │
│  └────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌────────────────────────┐  │
│  │WazuhManagerConfig│    │  WazuhConfiguration    │  │
│  │  (model)         │    │   (model)             │  │
│  └─────────────────┘    └────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Alert Sync Flow

```
User clicks "Force Sync" → View validates permissions
  → ManagerClient.authenticate() gets JWT token
  → ManagerClient.get_alerts(since=last_sync) fetches paginated alerts
  → For each alert:
       Check dedup by wazuh_alert_id
       Create Alert object if new
       Link to AlertSource if applicable
  → ManagerClient.get_agent_status() updates agent info
  → Create WazuhSyncLog record
  → Redirect back with success/error message
```

## Data Flow: Alert → Analyst

```
Wazuh Agent → Wazuh Manager → Wazuh Indexer
                                    ↓
                         Django fetch_wazuh_alerts()
                                    ↓
                              Alert table
                                    ↓
                          ┌─────────────────┐
                          │  L1 Analyst      │
                          │  (sees "new")    │
                          │  Acknowledge →   │
                          │  Escalate        │
                          └────────┬────────┘
                                   ↓ escalated_to
                          ┌─────────────────┐
                          │  L2 Analyst      │
                          │  Investigate →   │
                          │  Resolve/Close   │
                          └─────────────────┘
```

## Security Boundary

```
Internet
   │
   ▼ Strict HTTPS
Nginx (port 443) → (proxy_pass port 8091)
   │
   ▼
Django (port 8091) → PostgreSQL (port 5432, localhost)
Django → Wazuh Manager (port 55000, internal network)
Django → Wazuh Indexer (port 9200, internal network)
```

All external access terminates at Nginx. Django is not exposed directly. Wazuh credentials are stored encrypted in environment variables via `python-decouple`.
