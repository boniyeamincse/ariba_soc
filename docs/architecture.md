# Architecture

## System Overview

Ariba SOC is a unified Security Operations Center platform that integrates **Wazuh** (SIEM) with a custom **Django dashboard** for alert management, triage, and reporting.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Load Balancer (nginx)                      │
│                           Port 80/443                             │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
    ┌───────────▼───────────┐     ┌───────────▼───────────┐
    │   Ariba SOC (Django)  │     │   Wazuh Dashboard     │
    │   Port 8000 (internal)│     │   Port 5601 (8443)    │
    └───────────┬───────────┘     └───────────┬───────────┘
                │                             │
    ┌───────────▼───────────┐     ┌───────────▼───────────┐
    │      PostgreSQL       │     │   Wazuh Indexer        │
    │      Port 5432        │     │   (OpenSearch)         │
    └───────────────────────┘     │   Port 9200            │
                                  └───────────┬───────────┘
    ┌───────────────────────┐                 │
    │       Redis           │     ┌───────────▼───────────┐
    │       Port 6379       │     │   Wazuh Manager       │
    └───────────────────────┘     │   Ports 1514/1515/    │
                                  │   514/udp/55000       │
                                  └───────────────────────┘
```

## Components

### Ariba SOC (Django Application)
- **Web Server**: Gunicorn with 4 workers
- **Task Scheduler**: Custom loop for alert sync, cleanup, reports
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Static Files**: nginx with 30-day cache

### Wazuh Stack
- **Manager**: Alert collection, agent management, API
- **Indexer**: OpenSearch-based log storage and search
- **Dashboard**: Kibana-based visualization UI

## Data Flow

```
Agents/Endpoints → Wazuh Manager → Wazuh Indexer → Ariba SOC Scheduler → PostgreSQL
                                                                         ↓
                                                              Ariba SOC Dashboard
```

## Security Architecture

### Authentication
- Django session-based auth
- Password hashing: PBKDF2
- CSRF protection on all forms

### Authorization
- Role-Based Access Control (RBAC)
- Roles: SOC L1, SOC L2, SOC L3, Manager, Admin
- Permission checks at view and template level

### Data Protection
- Wazuh API credentials encrypted at rest (django-cryptography)
- SSL/TLS for all inter-service communication
- Secure cookies in production (HttpOnly, Secure, SameSite)

## Deployment Architecture

### Development
```bash
make setup          # Full stack with live reload
make logs           # Tail all logs
make test           # Run test suite
```

### Production
```bash
make prod-up        # Production stack
make health         # Verify all services
make backup         # Backup database + configs
```

## Scaling Considerations

| Component | Scaling Strategy |
|-----------|-----------------|
| Django Web | Horizontal (multiple Gunicorn workers) |
| PostgreSQL | Vertical + read replicas |
| Redis | Vertical + clustering |
| Wazuh Manager | Vertical (single-node limitation) |
| Wazuh Indexer | Horizontal (cluster mode) |

## Monitoring

- Health checks on all services
- Wazuh Indexer cluster health: `_cluster/health`
- Wazuh Manager API: `/manager/status`
- Application logs to stdout/stderr

## Disaster Recovery

1. **Backup**: `make backup` (database + Wazuh configs)
2. **Restore**: `make restore TIMESTAMP=<ts>`
3. **RTO**: ~15 minutes (full stack rebuild)
4. **RPO**: ~5 minutes (sync interval)
