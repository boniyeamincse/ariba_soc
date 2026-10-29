# 💻 Developer Guide: 01. System Architecture

## 1. High-Level Architecture Overview
Ariba SOC is built on an enterprise asynchronous microservice architecture comprising:

```mermaid
flowchart TD
    Endpoints["Monitored Endpoints<br/>(Wazuh Agents, Auditd, Web)"] -->|Encrypted TCP 1514| WazuhManager["Wazuh Manager (4.14.9)<br/>Analysisd Engine & Decoders"]
    WazuhManager -->|Filebeat HTTPS 9200| WazuhIndexer["Wazuh Indexer<br/>(OpenSearch 2.x Cluster)"]
    WazuhIndexer <-->|Dashboard 443/5601| WazuhDashboard["Wazuh Dashboard"]
    
    subgraph Ariba_SOC_Platform["Ariba SOC Core Platform"]
        Scheduler["Celery / Async Scheduler<br/>(Alert Ingestion & SLA Workers)"] -->|Polling HTTPS 9200| WazuhIndexer
        Scheduler -->|Save Normalized Events| PostgresDB[("PostgreSQL 15<br/>Relational Database")]
        Scheduler <-->|Task Queue & Alarms| Redis[("Redis 7 Cache / Broker")]
        
        DjangoWeb["Django 5.x Web Application<br/>(Gunicorn + Static Assets)"] <--> PostgresDB
        DjangoWeb <--> Redis
        Nginx["Nginx Reverse Proxy<br/>(Port 80/8080/443 SSL)"] --> DjangoWeb
    end
    
    AnalystBrowser["Analyst / SOC Browser"] --> Nginx
```

---

## 2. Core Service Components
- **`web`**: Django 5.x core application served via Gunicorn. Handles REST APIs, RBAC, Alert Cockpit, Kanban Board, PDF generation.
- **`scheduler`**: Asynchronous worker running periodic sync tasks:
  - Polling Wazuh Indexer (`wazuh-alerts-*`) every 10m/1m.
  - SLA breach evaluation and escalation engine.
  - Automated report generation and database pruning.
- **`db`**: PostgreSQL 15 database storing alerts, assets, audit trails, incidents, and settings.
- **`redis`**: In-memory broker handling real-time audio/visual alarm states, session caches, and Celery locks.
- **`nginx`**: Front-facing web server providing SSL termination, static file serving, and gzip compression.
