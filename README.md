# Ariba SOC Unified Security Stack

[![CI](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml/badge.svg)](https://github.com/boniyeamincse/ariba_soc/actions/workflows/ci.yml)
[![Security](https://github.com/boniyeamincse/ariba_soc/actions/workflows/security-scan.yml/badge.svg)](https://github.com/boniyeamincse/ariba_soc/actions/workflows/security-scan.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A fully containerized, end-to-end **Security Operations Center** platform integrating **Wazuh SIEM** with a custom **Django dashboard** for alert management, triage, and reporting.

---

## Features

- **Real-time Alert Sync** — Automatic synchronization from Wazuh Indexer every 5 minutes
- **Alert Triage** — Assign, escalate, and track security alerts
- **RBAC** — Role-based access control (L1/L2/L3 Analyst, Manager, Admin)
- **Audit Logging** — Complete audit trail of all actions
- **Reports** — Automated CSV/PDF report generation
- **Wazuh Integration** — Agent management, rule viewing, and health monitoring

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

# Start the stack
make setup
```

### Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Ariba SOC | http://localhost:8080 | admin / Admin@12345 |
| Wazuh Dashboard | https://localhost:8443 | admin / Admin@12345 |

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
│   ├── accounts/               # User management & RBAC
│   ├── alerts/                 # Alert models & workflows
│   ├── audit/                  # Audit logging
│   ├── config/                 # Django settings
│   ├── dashboard/              # Dashboard views
│   ├── monitor/                # Wallboard monitor
│   ├── reports/                # Report generation
│   ├── settings_manager/       # System configuration
│   ├── wazuh_integration/      # Wazuh API client & sync
│   ├── tests/                  # Test suite
│   ├── scripts/                # Utility scripts
│   ├── templates/              # HTML templates
│   ├── static/                 # CSS/JS assets
│   └── Dockerfile
├── infrastructure/
│   ├── docker-compose.yml      # Development stack
│   ├── docker-compose.prod.yml # Production stack
│   ├── config/                 # Nginx, Wazuh configs
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
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make logs           # Tail all logs
make test           # Run test suite
make lint           # Run linting
make format         # Auto-format code
make health         # Run health check
make backup         # Backup database
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



user the project :

https://localhost:8443/app/login?
user :admin
Pass :Admin@12345


http://localhost:8080/accounts/login/

user :admin
Pass :Admin@12345
