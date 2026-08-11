# Roadmap & Ideas

## Short Term (v1.1)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Celery-based scheduled sync | High | 2 days | Replace manual sync with periodic task |
| Alert archiving/retention | High | 1 day | Delete or archive alerts older than N days |
| Bulk alert operations | High | 2 days | Select multiple → status change, assign, close |
| Test coverage for reports | High | 1 day | Add tests for PDF/CSV views |
| Test coverage for audit | Medium | 1 day | Add tests for audit middleware |
| Test coverage for notifications | Medium | 1 day | Add tests for notification triggers |
| Server-side board pagination | Medium | 2 days | Load board cards in chunks |
| README badges for tests | Low | 0.5 day | Add coverage and status badges |

## Medium Term (v1.2)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Multi-Wazuh cluster support | High | 1 week | Multiple Manager/Indexer connections |
| Redis caching for dashboard | High | 2 days | Cache KPI queries, 5-min TTL |
| User notification preferences | Medium | 1 day | Per-user email/in-app toggle |
| IP whitelist middleware | Medium | 1 day | Restrict access by IP range |
| Password policy enforcement | Medium | 0.5 day | Min length, complexity, expiry |
| Session idle timeout | Medium | 0.5 day | Auto-logout after inactivity |
| PWA support | Medium | 3 days | Service worker, offline fallback, install prompt |
| Keyboard shortcuts | Low | 2 days | 'A' assign, 'E' escalate, 'N' next alert |

## Long Term (v2.0)

| Item | Priority | Effort | Notes |
|------|----------|--------|-------|
| Multi-tenancy (orgs) | High | 2 weeks | Isolate alerts/SOC teams by organization |
| Alert enrichment engine | High | 2 weeks | Custom enrichment rules, threat intel lookup |
| MITRE ATT&CK mapping | High | 1 week | Auto-map alerts to MITRE techniques |
| Custom dashboard widgets | Medium | 2 weeks | Drag-and-drop dashboard configurator |
| SOC playbook automation | Medium | 3 weeks | Automated response actions (API calls, scripts) |
| SLA dashboard | Medium | 1 week | Real-time SLA breach tracking per analyst |
| Webhook integrations | Medium | 1 week | Inbound webhooks from other tools (TheHive, Slack) |
| Advanced RBAC (groups) | Medium | 1 week | Role + group-based permissions (Django auth groups) |
| Audit log retention | Low | 1 day | Configurable audit log cleanup |
| Localization (i18n) | Low | 2 weeks | Multi-language support |

## Ideas (Not Yet Prioritized)

- **MFA/2FA** — TOTP or WebAuthn for login
- **Single Sign-On** — OAuth2/OIDC (Keycloak, Azure AD)
- **Mobile app** — React Native or Flutter companion
- **Real-time alerts via WebSocket** — Django Channels for live updates
- **Alert similarity clustering** — ML-based alert grouping
- **Threat intelligence feeds** — Pull from MISP, VirusTotal, AlienVault OTX
- **Automated report scheduling** — Weekly/monthly PDF emailed to stakeholders
- **CSV/Excel import** — Bulk ingest alerts from external sources
- **Alert templates** — Pre-defined response templates for common alert types
- **Calendar integration** — On-call schedule linked to alert assignment

## Contribution Ideas

Looking for ways to contribute? Pick any item from the lists above, or:

- Add test coverage for untested areas (reports, audit, notifications, settings)
- Improve error handling and user-facing error messages
- Add input validation and sanitization improvements
- Create a Helm chart for Kubernetes deployment
- Write end-to-end tests with Selenium or Playwright
- Improve accessibility (ARIA labels, keyboard navigation, screen reader support)
