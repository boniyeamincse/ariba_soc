# Known Limitations

## Functional Limitations

| Limitation | Impact | Planned Resolution |
|------------|--------|-------------------|
| **No real-time streaming** | Alerts polled on demand only (manual sync) | Add Celery beat for scheduled sync |
| **Single Wazuh server** | Only one Wazuh Manager/Indexer pair supported | Multi-cluster support in v2.0 |
| **No alert dedup across syncs** | Dedup works by `wazuh_alert_id`, but if Wazuh changes alert IDs, duplicates may occur | Add content-based hashing |
| **No multi-tenancy** | All analysts share the same alert pool | Future enterprise version |
| **No custom alert rules** | Alert severity/title determined by Wazuh rules | Alert enrichment engine |
| **No notification preferences** | Notifications are all-or-nothing | Per-user notification settings |
| **Single database** | No read replica support | Database read replicas |

## Technical Limitations

| Limitation | Impact | Notes |
|------------|--------|-------|
| **SQLite in dev only** | No concurrent writes, limited performance | Always use PostgreSQL for staging/production |
| **Polling-based sync** | No real-time alert ingestion | Wazuh 4.x does not support webhooks natively |
| **Single-threaded sync** | Large sync operations block the request | Move to Celery background task |
| **No pagination on board view** | Board shows all alerts; slow with 10k+ alerts | Add server-side pagination |
| **No alert archiving** | Alerts accumulate indefinitely | Add archiving/retention policy |
| **No rate limiting** | API endpoints have no rate limits | Add Django Ratelimit middleware |
| **No caching** | Dashboard queries DB on every load | Add Redis caching layer |
| **No mobile app** | Mobile browser experience is usable but not optimized | Progressive Web App (PWA) |

## Security Limitations

| Limitation | Impact | Notes |
|------------|--------|-------|
| **No MFA** | Password-only authentication | Add TOTP or WebAuthn |
| **No IP whitelisting** | Any authenticated user can access from anywhere | Add IP restrictions |
| **Password policy** | Django defaults only | Custom password validation |
| **No session timeout** | Sessions persist until browser close | Add idle timeout middleware |
| **Wazuh SSL verification disabled** | Self-signed certs used; `verify=False` | Provide CA cert for verification |

## UI/UX Limitations

| Limitation | Impact | Notes |
|------------|--------|-------|
| **No dark/light toggle** | Dark theme only | Future enhancement |
| **No keyboard shortcuts** | All operations require mouse | Add hotkeys for power users |
| **No bulk operations** | Alerts managed one at a time | Bulk status change, assign, close |
| **No CSV import** | No way to import alerts from other sources | Future enhancement |
| **No custom dashboard widgets** | Fixed dashboard layout | Customizable dashboard |

## Testing Limitations

| Limitation | Impact | Notes |
|------------|--------|-------|
| **No test coverage for reports** | Report PDF/CSV views untested | High priority to add |
| **No test coverage for audit** | Audit middleware and models untested | Medium priority |
| **No test coverage for notifications** | Notification system untested | Medium priority |
| **No test coverage for settings** | Settings manager untested | Medium priority |
| **No integration tests with live Wazuh** | Tests use mocks | Add integration test suite |
