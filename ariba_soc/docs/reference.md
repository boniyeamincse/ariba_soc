# Reference

## Glossary

| Term | Definition |
|------|------------|
| **SIEM** | Security Information and Event Management |
| **SOC** | Security Operations Center |
| **Wazuh** | Open-source security monitoring platform (fork of OSSEC) |
| **Manager** | Wazuh component — manages agents, processes alerts, hosts the REST API |
| **Indexer** | Wazuh component — OpenSearch cluster for alert storage and search |
| **Agent** | Wazuh endpoint software installed on monitored hosts |
| **L1 Analyst** | Level 1 SOC analyst — first-line triage |
| **L2 Analyst** | Level 2 SOC analyst — deep investigation and response |
| **RBAC** | Role-Based Access Control |
| **REST API** | Representational State Transfer API |
| **JWT** | JSON Web Token |
| **OpenSearch** | Fork of Elasticsearch used by Wazuh for indexing |
| **Kanban** | Visual workflow management board |
| **SLA** | Service Level Agreement |
| **MFA** | Multi-Factor Authentication |
| **PWA** | Progressive Web Application |
| **Gunicorn** | Green Unicorn — Python WSGI HTTP server |
| **WeasyPrint** | HTML/CSS to PDF converter for Python |
| **TOTP** | Time-based One-Time Password |
| **DSL** | Domain-Specific Language (OpenSearch query DSL) |

## Key Acronyms

| Acronym | Full Form |
|---------|-----------|
| API | Application Programming Interface |
| CSRF | Cross-Site Request Forgery |
| CSV | Comma-Separated Values |
| ERD | Entity-Relationship Diagram |
| HTTPS | Hypertext Transfer Protocol Secure |
| JSON | JavaScript Object Notation |
| KPI | Key Performance Indicator |
| MVT | Model-View-Template |
| N/A | Not Applicable |
| PDF | Portable Document Format |
| PK | Primary Key |
| SQL | Structured Query Language |
| SSL | Secure Sockets Layer |
| TLS | Transport Layer Security |
| UI | User Interface |
| UX | User Experience |
| URL | Uniform Resource Locator |
| VCS | Version Control System |
| WSGI | Web Server Gateway Interface |
| XSS | Cross-Site Scripting |

## External References

| Resource | URL |
|----------|-----|
| Django Documentation | https://docs.djangoproject.com/en/4.2/ |
| Wazuh Documentation | https://documentation.wazuh.com/current/ |
| Wazuh API Reference | https://documentation.wazuh.com/current/user-manual/api/reference.html |
| OpenSearch Documentation | https://opensearch.org/docs/latest/ |
| OpenSearch Security | https://opensearch.org/docs/latest/security-plugin/index/ |
| Bootstrap 5 | https://getbootstrap.com/docs/5.3/ |
| WeasyPrint | https://doc.courtbouillon.org/weasyprint/ |
| Gunicorn | https://docs.gunicorn.org/en/stable/ |
| Nginx | https://nginx.org/en/docs/ |
| python-decouple | https://pypi.org/project/python-decouple/ |
| PostgreSQL | https://www.postgresql.org/docs/15/ |
| Docker | https://docs.docker.com/ |

## Ports Reference

| Port | Service | Purpose |
|------|---------|---------|
| 55000 | Wazuh Manager | REST API (JWT auth) |
| 9200 | Wazuh Indexer | OpenSearch API (Basic auth) |
| 8091 | Django (Gunicorn) | Application server |
| 443 | Nginx | HTTPS (reverse proxy) |
| 5432 | PostgreSQL | Database |
| 587 | SMTP | Email notifications |

## File Paths Reference

| Path | Purpose |
|------|---------|
| `/opt/ariba_soc/` | Production install directory |
| `/opt/ariba_soc/.env` | Environment configuration |
| `/opt/ariba_soc/venv/` | Python virtual environment |
| `/opt/ariba_soc/staticfiles/` | Collected static assets |
| `/var/log/ariba-soc/` | Gunicorn logs |
| `/etc/systemd/system/ariba-soc.service` | Systemd service unit |
| `/etc/nginx/sites-available/ariba-soc` | Nginx config |
| `/var/ossec/api/configuration/rbac/rbac.db` | Wazuh RBAC database |
