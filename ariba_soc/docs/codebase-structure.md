# Codebase Structure

## Root Directory

```
ariba_soc/
├── accounts/              # User authentication, profiles, role management
├── alerts/                # Alert models, views (table/board), comments, notifications
├── audit/                 # Audit logging middleware + models
├── config/                # Django settings, root URL config, WSGI/ASGI
├── dashboard/             # Statistics, charts, KPIs
├── deploy/                # Nginx config, systemd service, Docker
├── docs/                  # Documentation (24 files)
├── reports/               # PDF/CSV report generation
├── settings_manager/      # Dynamic system settings management
├── wazuh_integration/     # Wazuh Manager + Indexer client integration
├── static/                # Static assets (CSS, JS, images)
│   ├── css/               # ariba-soc.css (glassmorphism theme)
│   ├── js/                # ariba-soc.js (client-side interactivity)
│   └── images/            # Favicon, logos, patterns
├── templates/             # Django templates
│   ├── base.html          # Base template with navbar
│   ├── registration/      # Login/logout templates
│   └── ariba_soc/         # App-specific templates
├── requirements.txt       # Python dependencies
├── manage.py              # Django CLI entry point
├── .env                   # Environment variables (not in VCS)
└── .github/workflows/     # CI pipeline
```

## App-by-App Breakdown

### `accounts/`

| File | Purpose |
|------|---------|
| `models.py` | `AnalystProfile` (role, phone, avatar), `ROLE_CHOICES`, `WAZUH_ALLOWED_ROLES` |
| `views.py` | Profile view, admin user management |
| `decorators.py` | `@role_required(*roles)` decorator |
| `signals.py` | Auto-create `AnalystProfile` on user creation |
| `admin.py` | Inline profile admin |
| `urls.py` | Profile routes |
| `tests.py` | Auth tests |

### `alerts/`

| File | Purpose |
|------|---------|
| `models.py` | `Alert`, `AlertComment`, `AlertAuditLog`, `Notification`, `AlertSource` |
| `views.py` | `alert_table`, `alert_board`, `my_alerts`, `alert_detail`, `edit_alert_ajax`, `assign_ajax` |
| `forms.py` | `AlertSearchForm`, `AlertFilterForm` |
| `urls.py` | All alert routes |
| `admin.py` | Alert admin config |
| `tests.py` | Alert CRUD tests |

### `audit/`

| File | Purpose |
|------|---------|
| `models.py` | `AuditLog` with action choices |
| `middleware.py` | `AuditMiddleware` — logs every request |
| `views.py` | Audit log viewer |
| `urls.py` | Audit routes |
| `admin.py` | Admin config |

### `config/`

| File | Purpose |
|------|---------|
| `settings.py` | Django settings (DB, apps, middleware, static files, etc.) |
| `urls.py` | Root URL configuration |
| `wsgi.py` | WSGI application for Gunicorn |
| `asgi.py` | ASGI application |

### `dashboard/`

| File | Purpose |
|------|---------|
| `views.py` | `dashboard_home` (stats + aggregates), chart data APIs |
| `urls.py` | Dashboard routes |
| `tests.py` | Dashboard tests |

### `reports/`

| File | Purpose |
|------|---------|
| `views.py` | `generate_report` (alert report), `analyst_performance_report` |
| `utils.py` | PDF rendering (WeasyPrint), CSV streaming |
| `urls.py` | Report routes |

### `settings_manager/`

| File | Purpose |
|------|---------|
| `models.py` | `SystemSetting`, `SettingAuditLog` |
| `views.py` | Settings list/edit views |
| `urls.py` | Settings routes |
| `admin.py` | Admin config |

### `wazuh_integration/`

| File | Purpose |
|------|---------|
| `models.py` | `WazuhManagerConfig`, `WazuhConfiguration` (Indexer), `WazuhSyncLog` |
| `services.py` | `ManagerClient`, `IndexerClient`, `fetch_wazuh_alerts` |
| `views.py` | Config views, test connections, sync trigger |
| `forms.py` | `WazuhManagerConfigForm`, `WazuhConfigurationForm` |
| `urls.py` | 8 URL patterns |
| `admin.py` | Admin config |
| `tests.py` | 19 integration tests |

## Key Configuration Files

| File | Purpose |
|------|---------|
| `.env` | DB creds, Wazuh creds, secret key, debug flag |
| `requirements.txt` | Python packages (Django, WeasyPrint, requests, psycopg2, etc.) |
| `.github/workflows/ci.yml` | GitHub Actions CI |
| `deploy/nginx.conf` | Nginx reverse proxy config |
| `deploy/ariba-soc.service` | systemd unit file |
| `deploy/Dockerfile` | Docker build |
| `deploy/docker-compose.yml` | Docker Compose (app + PostgreSQL) |
