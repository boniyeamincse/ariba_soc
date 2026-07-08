# DOC-01: No README.md at Project Root

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Documentation

## Current Problem
The project root at `/home/boni/Desktop/siem/ariba_soc/` has no `README.md` file. A new developer or operator cloning the repository has zero information about:
- What the project is (SOC dashboard)
- How to set up the development environment
- Required environment variables
- How to run the application
- How to run tests
- How to deploy

The only documentation files in the repo are `docs/AI.md` (AI assistant notes) and `docs/setting_menu_ui.md` (outdated UI spec), neither of which serve as a project introduction.

## Expected Behavior
A comprehensive `README.md` at the project root should include:
1. Project title and description
2. Architecture overview (apps, models, external dependencies)
3. Prerequisites (Python 3.11+, PostgreSQL, Redis)
4. Quick start guide (clone, venv, migrate, seed, run)
5. Environment variables table
6. Testing instructions
7. Deployment instructions
8. Contributing guidelines

## Affected Files
- `README.md` (needs to be created at project root)

## Suggested Fix
```markdown
# Ariba SOC Dashboard

A Django-based Security Operations Center (SOC) dashboard for alert triage, 
Wazuh SIEM integration, analyst workflow management, and reporting.

## Architecture

| App | Purpose |
|-----|---------|
| `accounts` | User profiles, RBAC, role permissions |
| `alerts` | Alert CRUD, board, SLA tracking, escalation |
| `wazuh_integration` | Wazuh API client, alert sync |
| `settings_manager` | All configuration UIs (severity, SLA, notifications) |
| `dashboard` | Management dashboard with KPIs and charts |
| `reports` | CSV/Excel export, scheduled reports |
| `audit` | Audit logging middleware and settings |

## Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for development)
- Redis 7+ (optional, for caching)
- Wazuh 4.x (optional, for alert integration)

## Quick Start

```bash
cp .env.example .env
# Edit .env with your settings
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_alerts
python manage.py createsuperuser
python manage.py runserver
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | (required) | Django secret key |
| `DATABASE_ENGINE` | `postgresql` | DB engine or `sqlite3` |
| `WAZUH_API_URL` | — | Wazuh API base URL |
```

## QA Verification
1. The `README.md` must render correctly on GitHub (markdown formatting).
2. A new developer following the Quick Start must get the app running in <10 minutes.
3. All links in the README must be valid.
