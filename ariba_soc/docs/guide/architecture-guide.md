# Platform Architecture Guide

This document outlines the high-level text-based architecture of the Ariba SOC platform.

## High-Level Architecture Diagram

```mermaid
graph TD
    %% External Interfaces
    User([SOC Analyst / Admin]) -->|HTTPS / Port 80, 443| Nginx[Nginx Reverse Proxy]
    
    %% Web Server Layer
    Nginx -->|WSGI Proxy| Gunicorn[Gunicorn WSGI Server]
    Nginx -->|Static Assets| StaticFiles[(Static / Media Files)]
    
    %% Application Layer
    subgraph "Ariba SOC Application (Django)"
        Gunicorn --> DjangoCore[Django Backend]
        
        DjangoCore --> Auth[Accounts & RBAC]
        DjangoCore --> Alerts[Alert Management]
        DjangoCore --> Settings[Settings Manager]
        DjangoCore --> Dash[Dashboard & Reporting]
        DjangoCore --> Audit[Audit Logging]
        
        %% Integration Layer
        DjangoCore --> WazuhInt[Wazuh Integration Module]
    end
    
    %% Database Layer
    DjangoCore -->|ORM| Database[(PostgreSQL / SQLite)]
    
    %% External SIEM
    WazuhInt <-->|REST API / Port 55000| WazuhManager{Wazuh Manager}
    
    %% Data Flow Styling
    classDef internal fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef external fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef db fill:#334155,stroke:#eab308,stroke-width:2px,color:#f8fafc;
    
    class DjangoCore,Auth,Alerts,Settings,Dash,Audit,WazuhInt internal;
    class WazuhManager,User external;
    class Database,StaticFiles db;
```

## Directory Structure Architecture

Below is the standard ASCII representation of the core project structure:

```text
ariba_soc/
├── config/                 # Main Django project settings & URLs
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/               # User profiles, RBAC, and Authentication
├── alerts/                 # Alert ingestion, Kanban board, Triage logic
├── audit/                  # Platform-wide action auditing
├── dashboard/              # KPI metrics and analytics
├── reports/                # PDF/CSV generation
├── settings_manager/       # Centralized SOC configuration
├── wazuh_integration/      # Wazuh API client and sync logic
├── templates/              # Global UI templates (base.html, etc.)
├── static/                 # CSS (ariba-soc.css), JS, and vendor assets
├── media/                  # User avatars and uploaded files
├── docs/                   # Platform documentation
│   └── guide/              # This directory
├── .env                    # Environment variables (DB credentials, API keys)
├── manage.py               # Django execution script
└── requirements.txt        # Python dependencies
```

## Component Breakdown

1. **Nginx & Gunicorn (Web Layer):** Nginx acts as the reverse proxy, serving static files efficiently and forwarding dynamic application requests to Gunicorn, which runs the Django WSGI application.
2. **Django Backend (Core Layer):** Contains modular apps ensuring separation of concerns. `alerts` handles the SOC operational workflow, `settings_manager` dynamically configures platform rules, and `accounts` enforces Role-Based Access Control (RBAC).
3. **Database (Persistence Layer):** Stores all internal state, including alert histories, user profiles, audit logs, and configuration matrices.
4. **Wazuh Manager (Integration Layer):** The external SIEM engine. Ariba SOC periodically polls the Wazuh REST API via the `wazuh_integration` module to fetch new security events and translate them into actionable SOC alerts.
