# Ariba SOC Unified Security Stack

[![CI](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml/badge.svg)](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml)
[![Security](https://github.com/boniyeamincse/ariba_soc/actions/workflows/security-scan.yml/badge.svg)](https://github.com/boniyeamincse/ariba_soc/actions/workflows/security-scan.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully containerized, end-to-end **Security Operations Center** platform integrating **Wazuh SIEM** with a custom **Django dashboard** for alert management, triage, threat hunting, vulnerability and incident handling, and reporting.

---

## Features

### Alert Management & Triage
- **Real-time alert sync** from the Wazuh Indexer (scheduler runs every 5 minutes)
- **Aggregation & de-duplication** of repeated/related alerts
- **Severity mapping** from Wazuh rule levels to SOC severities
- **Full lifecycle controls** — status, verdict, assignment (self/others/teams) and the L1 → L2 → L3 → Manager **escalation path**
- **Comments, watchers and @mentions**, plus a complete per-alert audit trail and transition history
- **Bulk actions** and single-alert move API

### SLA Management
- **Acknowledgement & resolution SLA** timers per severity (configurable)
- **Breach automation** — background job detects overdue alerts and raises **auto-escalations**
- Assigning an alert automatically records its **acknowledgement**, so ack-SLA is met for alerts already in an escalated state

### Routing & Assignment
- **Configurable routing rules** matching on rule, severity, source and MITRE tactic
- **Least-loaded analyst** auto-assignment for routed alerts

### Notifications
- **Multi-channel notifications** (email / webhook) on assignment, escalation and SLA breach
- **Per-user notification preferences**

### Enrichment
- **IOC enrichment** (e.g. VirusTotal) with enrichment **status and error tracking**

### Investigation Tooling
- **Saved filters, tags and bookmarks**
- **CSV/PDF export** and per-alert **PDF report** generation
- **Evidence attachments**, watchers and @mentions on alerts
- **Related-alert detection** with **merge / unmerge** of duplicates
- **Per-rule response playbooks/SOP** and a **false-positive feedback loop** (noisy-rule reporting)

### Threat Hunting
- **Live search** across normalized events with a dedicated **event detail** view

### Vulnerability Management
- **Inventory** of vulnerabilities and **affected assets**, CVE list and manual/automated **sync**
- Workflow actions: **assign, remediate, accept-risk, verify, reopen, mark false-positive**

### Incident Management
- Incident **creation, assignment, status transitions, timeline and notes**, linked to alerts

### Reports & Metrics
- **MTTA / MTTR** dashboards with **CSV/Excel export**
- Scheduled report generation and downloadable reports

### Wazuh Integration
- **Agent management**, **rule viewing** and **health monitoring**
- Manager and Indexer **connectivity tests**
- **Active response** execution and execution **history**
- Editable manager configuration

### RBAC, Audit & Monitoring
- **Role-based access control** — L1/L2/L3 Analyst, SOC Manager, SOC Engineer, Admin, Viewer, Monitor
- **SOC team** management and **shift handover** logging
- **Audit logging** middleware capturing all actions

### Configuration
- Admin-managed settings for severity/status/verdict, SLA, escalation, notification, dashboard, alarm, report, IOC enrichment, alert aggregation, suppression rules, routing rules and playbooks

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Linux host with `vm.max_map_count=262144`

```bash
# Set kernel parameter
sudo sysctl -w vm.max_map_count=262144

# Clone and setup
git clone git@github.com:boniyeamincse/ariba_soc.git
cd ariba_soc

# Copy environment files
cp .env.example infrastructure/.env
cp ariba_soc/.env.example ariba_soc/.env

# Start the stack (certs + start + seed + migrate)
make setup

# Create the dashboard superuser
make createsuperuser
```

### Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Ariba SOC | http://localhost:8080 | superuser created via `make createsuperuser` |
| Wazuh Dashboard | https://localhost:8443 | admin / Admin@12345 |
| Django admin | http://localhost:8080/admin/ | superuser created via `make createsuperuser` |

> Change the default Wazuh dashboard credentials and set a strong Django superuser password before any non-local deployment.

---

## Project Structure

```
ariba_soc/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Lint, test, build
│   │   ├── security-scan.yml   # Trivy, CodeQL, dependency audit
│   │   ├── docker-publish.yml  # Docker Hub publish
│   │   └── deploy.yml          # Deployment pipeline
│   └── dependabot.yml          # Automated dependency updates
├── ariba_soc/                  # Django application
│   ├── accounts/               # Users, RBAC, teams, shift handover
│   ├── alerts/                 # Alerts, SLA, routing, evidence, merge, playbooks
│   ├── audit/                  # Audit logging
│   ├── config/                 # Django settings & root URLconf
│   ├── dashboard/              # Tier dashboards & stats
│   ├── hunting/                # Live search & event detail
│   ├── incidents/              # Incident management
│   ├── vulnerabilities/        # Vulnerability cases
│   ├── monitor/                # Wallboard monitor & globe
│   ├── reports/                # MTTA/MTTR & report exports
│   ├── settings_manager/       # System configuration & routing/playbooks
│   ├── wazuh_integration/      # Wazuh API client, sync & active response
│   ├── docker/                 # entrypoint.sh, scheduler.sh
│   ├── tests/                  # Test suite
│   ├── scripts/                # Utility scripts
│   ├── templates/              # HTML templates
│   ├── static/                 # CSS/JS assets
│   └── Dockerfile
├── infrastructure/
│   ├── docker-compose.yml      # Development stack
│   ├── docker-compose.override.yml
│   ├── docker-compose.prod.yml # Production stack
│   ├── config/                 # Nginx, Wazuh (rules, dashboard) configs
│   └── scripts/                # Operational scripts
├── docs/
│   ├── architecture.md         # System architecture
│   ├── api.md                  # API reference
│   ├── runbook.md              # Incident response
│   └── production-deployment-guide.md
├── .editorconfig               # Code style
├── .pre-commit-config.yaml     # Git hooks
├── Makefile                    # Development commands
├── LICENSE                     # MIT License
├── SECURITY.md                 # Security policy
├── CONTRIBUTING.md             # Contribution guide
└── README.md
```

---

## Development Commands

```bash
# Show all available commands
make help

# Common commands
make build           # Build Docker images
make up              # Start all services
make down            # Stop all services
make restart-web     # Restart web + scheduler
make logs            # Tail all logs
make test            # Run test suite
make lint            # Run linting
make format          # Auto-format code
make migrate         # Run Django migrations
make createsuperuser # Create Django superuser
make health          # Run health check
make status          # Show container status
make backup          # Backup database
make restore TIMESTAMP=<ts>  # Restore backup
```

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | (required) |
| `DJANGO_CRYPTOGRAPHY_KEY` | Encryption key | (required) |
| `DATABASE_PASSWORD` | PostgreSQL password | ariba_soc |
| `WAZUH_API_PASSWORD` | Wazuh Manager API password | (required) |
| `WAZUH_INDEXER_PASSWORD` | Wazuh Indexer password | (required) |

### Generate Secrets

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Deployment

### Local Development

```bash
make setup
```

### Production

```bash
# Edit production env
cp .env.example infrastructure/.env
vim infrastructure/.env

# Start production stack
make prod-up

# Verify
make health
```

### Remote Deployment

```bash
make deploy SERVER=user@server-ip
```

---

## API Reference

See [docs/api.md](docs/api.md) for complete API documentation.

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for system design details.

---

## Incident Response

See [docs/runbook.md](docs/runbook.md) for operational runbooks.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

---

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting policy.

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.
