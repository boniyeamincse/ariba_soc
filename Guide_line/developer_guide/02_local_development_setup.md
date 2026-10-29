# 💻 Developer Guide: 02. Local Development Setup

## 1. Prerequisites
- Docker Engine 24.0+ and Docker Compose v2.
- Python 3.11+ (recommended for local virtualenvs and tooling).
- Git.

---

## 2. Quick Start
From the project root:
```bash
cd infrastructure
docker compose up -d
```

### Checking Container Health:
```bash
docker ps
```
All containers (`infrastructure-web-1`, `infrastructure-scheduler-1`, `infrastructure-db-1`, `infrastructure-redis-1`, `wazuh.manager`, `wazuh.indexer`) should show status `Up (healthy)`.

---

## 3. Useful Development Commands

### Django Checks & Migrations:
```bash
# System check:
docker exec infrastructure-web-1 python manage.py check

# Create and apply migrations:
docker exec infrastructure-web-1 python manage.py makemigrations
docker exec infrastructure-web-1 python manage.py migrate

# Create superuser:
docker exec -it infrastructure-web-1 python manage.py createsuperuser
```

### Running Test Suite:
```bash
# Run all alert & integration tests:
docker exec infrastructure-web-1 python manage.py test alerts wazuh_integration
```

### Accessing Database & Django Shell:
```bash
# Django Interactive Shell:
docker exec -it infrastructure-web-1 python manage.py shell

# PostgreSQL CLI:
docker exec -it infrastructure-db-1 psql -U ariba_soc -d ariba_soc
```
