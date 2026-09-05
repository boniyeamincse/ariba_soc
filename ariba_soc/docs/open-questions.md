# Open Questions

These are architectural and design decisions that remain unresolved and need stakeholder input.

## Architecture

1. **Should we switch from polling to WebSocket-based real-time updates?**
   - Pro: Instant alert delivery to analysts
   - Con: Requires Django Channels, Redis, more infrastructure
   - Status: Open — pending performance assessment at scale

2. **Should alert sync move to a background task queue?**
   - Currently blocks the request thread during sync
   - Option: Celery + Redis (already noted in roadmap)
   - Question: Is RabbitMQ preferred over Redis as broker?

3. **Should we support multiple Wazuh clusters?**
   - Current: Single Manager + Indexer pair
   - Future: Would require merging alerts from multiple clusters into a unified queue
   - Question: Cross-cluster dedup strategy?

## Security

4. **Should Wazuh SSL verification be mandatory?**
   - Currently disabled (`verify=False`) due to self-signed Wazuh certs
   - Option: Distribute Wazuh CA cert to Django hosts and enable verification
   - Question: Who manages CA cert rotation?

5. **Should we implement MFA?**
   - Currently password-only
   - Options: TOTP (Google Authenticator), WebAuthn (hardware keys), email OTP
   - Question: Which method? Should it be optional or mandatory?

6. **Should there be IP-based access restrictions?**
   - Currently any authenticated user can access from anywhere
   - Option: Restrict to SOC VPN/IP range
   - Question: Dynamic IPs allowed? What about remote analysts?

## Data & Retention

7. **What is the alert retention policy?**
   - No current archiving mechanism
   - Options: 30/60/90 day retention, archive to cold storage, delete oldest
   - Question: Compliance requirements for retention?

8. **Should we store the full Wazuh alert JSON in `raw_data`?**
   - Currently stored as JSONField — can be large (100KB+ per alert)
   - Option: Store only parsed fields, reference Wazuh Indexer for raw data
   - Question: Storage cost vs. convenience trade-off?

## Operations

9. **Should we add a dedicated health check endpoint?**
   - Currently no `/api/health/` endpoint
   - Needed for load balancers, monitoring (Nagios, Prometheus)
   - Question: What should the health check verify (DB, Wazuh connections)?

10. **Should we implement Prometheus metrics?**
    - Currently no metrics export
    - Useful for: alert volume monitoring, performance tracking
    - Question: Which metrics matter most?

## Features

11. **Should notifications support Slack/Teams integration?**
    - Currently in-app + email only
    - Question: Is there a preference for a chat platform?

12. **Should we support alert tagging/labeling?**
    - Currently no custom categorization beyond severity and source
    - Options: User-defined tags, MITRE ATT&CK tags, auto-tagging rules
    - Question: What tagging taxonomy?

13. **Should analysts be able to collaborate on alerts in real-time?**
    - Currently only threaded comments
    - Option: Real-time collaboration via WebSocket
    - Question: Is this a priority?

## Testing & Quality

14. **Should we add end-to-end tests?**
    - Currently unit tests only
    - Options: Selenium, Playwright, Cypress
    - Question: Critical user flows to cover?

15. **Should we enforce code coverage thresholds?**
    - Currently no coverage requirements
    - Question: What minimum coverage %? Which areas must be 100%?
