# 🛡️ Ariba SOC

[![Build](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml/badge.svg)](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2%2B-green)](https://djangoproject.com)
[![License](https://img.shields.io/badge/License-Proprietary-red)](LICENSE)

Ariba SOC is a modern **Security Information and Event Management (SIEM)** web application built for Security Operations Centers. It integrates with **Wazuh** to provide real-time alert triage, automated escalations, role-based access control (RBAC), kanban-style incident boards, and rich reporting.

> **Current version:** 1.0 — fully integrated with Wazuh Manager (API) + Indexer (OpenSearch).

---

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| **Wazuh Dual Connection** | Manager Client (API JWT on port 55000) + Indexer Client (OpenSearch Basic Auth on port 9200) |
| **Alert Sync Engine** | Scheduled + manual sync with dedup, pagination, and full audit trail |
| **Kanban Alert Board** | Drag-and-drop triage board with per-analyst columns and real-time updates |
| **RBAC** | 4 tiers: Admin, Manager, L2 Analyst, L1 Analyst — per-object permission checks |
| **Notifications** | In-app bell + automated email on assignment/status changes |
| **Reports** | PDF/CSV export for alerts, analyst performance, and compliance |
| **Settings Manager** | Centralized config for SLAs, escalation rules, alert sources, platform settings |
| **Audit Logging** | Every action (status change, assignment, config edit) logged for compliance |
| **Dark Glassmorphism UI** | Premium Bootstrap 5 theme with blur effects and responsive design |

---

## 🛠 Technology Stack

- **Backend:** Python 3.10+, Django 4.2
- **Database:** PostgreSQL 15 (production), SQLite (dev/test)
- **SIEM Engine:** Wazuh 4.x (Manager REST API + Indexer OpenSearch API)
- **Frontend:** HTML5, Bootstrap 5, Vanilla CSS (glassmorphism), vanilla JS
- **Deployment:** Nginx + Gunicorn, Docker, systemd
- **CI/CD:** GitHub Actions (runs 19 tests against PostgreSQL 15)

---

## 📁 Project Layout

```
ariba_soc/
├── accounts/          # User auth, profiles, roles
├── alerts/            # Alert models, views, kanban board
├── audit/             # Audit logging middleware + models
├── config/            # Django settings, URLs, WSGI/ASGI
├── dashboard/         # Statistics, charts, KPIs
├── deploy/            # Nginx config, systemd service, Docker
├── reports/           # PDF/CSV report generation
├── settings_manager/  # Dynamic system settings
├── wazuh_integration/ # Wazuh Manager + Indexer dual clients
├── static/            # CSS, JS, images
├── templates/         # All Django templates
└── docs/              # Full documentation suite (24 files)
```

---

## 🚀 Quickstart

```bash
git clone https://github.com/boniyeamincse/ariba_soc.git
cd ariba_soc
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8090
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Project Overview](docs/project-overview.md) | Vision, scope, target users |
| [Feature Status](docs/feature-status.md) | Implementation status of every feature |
| [System Architecture](docs/system-architecture.md) | Django MVT, Wazuh dual connection, data flow |
| [Codebase Structure](docs/codebase-structure.md) | Directory layout, key files, app responsibilities |
| [Installation Guide](docs/installation-guide.md) | Full setup — dev, staging, production |
| [Configuration Guide](docs/configuration-guide.md) | Environment variables, Wazuth creds, settings |
| [Database Documentation](docs/database-documentation.md) | ERD, all tables, migrations, indexes |
| [API Documentation](docs/api-documentation.md) | Internal + Wazuh API endpoints |
| [UI & User Guide](docs/ui-and-user-guide.md) | Screens, kanban board, navigation |
| [Auth & Authorization](docs/authentication-and-authorization.md) | Login flows, RBAC, role matrix |
| [Alert Management](docs/alert-management.md) | Lifecycle, status workflow, dedup |
| [Integrations](docs/integrations.md) | Wazuh Manager + Indexer setup |
| [Security](docs/security-documentation.md) | HTTPS, credential storage, audit |
| [Testing Guide](docs/testing-guide.md) | Running tests, CI pipeline |
| [Deployment & Operations](docs/deployment-and-operations.md) | Nginx, Gunicorn, Docker, monitoring |
| [Troubleshooting](docs/troubleshooting.md) | Common issues and fixes |
| [Contribution Guide](docs/contribution-guide.md) | Coding standards, PR workflow |
| [Known Limitations](docs/known-limitations.md) | Current gaps and constraints |
| [Roadmap & Ideas](docs/roadmap-and-ideas.md) | Future features and priorities |
| [Open Questions](docs/open-questions.md) | Decisions still to be made |
| [Reference](docs/reference.md) | Key terms, acronyms, external links |

---

## 📄 License

Proprietary — authorized SOC environments only. All rights reserved.
