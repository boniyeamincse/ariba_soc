# Wazuh Integration Module

## Purpose

Dual-connection integration with Wazuh — connects to both the Manager (REST API, JWT auth) and Indexer (OpenSearch API, Basic Auth) for alert ingestion and management.

## Key Models

### `WazuhManagerConfig`
| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Config label |
| `api_url` | URLField | Manager API base URL (e.g., `https://10.24.66.2:55000`) |
| `username` | CharField(255) | Wazuh API user |
| `password` | CharField(255) | Stored in DB (use env vars in production) |
| `is_active` | BooleanField | Only one config should be active |
| `created_at` / `updated_at` | DateTimeField | Auto timestamps |

### `WazuhConfiguration` (Indexer)
| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField(100) | Config label |
| `api_url` | URLField | Indexer API URL (e.g., `https://10.24.66.2:9200`) |
| `username` | CharField(255) | OpenSearch user |
| `password` | CharField(255) | OpenSearch password |
| `verify_ssl` | BooleanField | Verify SSL cert (default: False) |
| `is_active` | BooleanField | Only one active |

### `WazuhSyncLog`
Tracks each sync operation:
- triggered_by, status, alerts_fetched, alerts_created, alerts_skipped, error_message
- started_at, completed_at

## Key Services (`services.py`)

### `ManagerClient`
```python
class ManagerClient:
    def authenticate(self) -> str
        # POST /security/user/authenticate → JWT

    def get_alerts(self, since=None, limit=500) -> list
        # GET /security/alerts?limit=N&offset=...
        # Paginated, returns parsed alert list

    def get_agent_status(self) -> list
        # GET /agents?status=active
```

### `IndexerClient`
```python
class IndexerClient:
    def search(self, query: dict) -> dict
        # POST /wazuh-alerts-*/_search

    def cluster_health(self) -> dict
        # GET /_cluster/health
```

### `fetch_wazuh_alerts`
Orchestration function:
1. Gets active Manager config
2. ManagerClient.authenticate()
3. ManagerClient.get_alerts(since=last_sync)
4. Dedup by wazuh_alert_id
5. Creates Alert records
6. Creates WazuhSyncLog

## Key Views

| URL | Description |
|-----|-------------|
| `/wazuh/status/` | Integration status page with tabs |
| `/wazuh/manager-config/create/` | Create Manager config |
| `/wazuh/manager-config/<id>/edit/` | Edit Manager config |
| `/wazuh/indexer-config/create/` | Create Indexer config |
| `/wazuh/indexer-config/<id>/edit/` | Edit Indexer config |
| `/wazuh/test-manager/` | Test Manager connection |
| `/wazuh/test-indexer/` | Test Indexer connection |
| `/wazuh/sync/` | Force sync alerts |

## Test Connection Flow

**Manager:**
```
POST /wazuh/test-manager/
  → ManagerClient.authenticate() (tests credentials)
  → ManagerClient.get_agent_status() (tests API access)
  → Returns {"status": "ok"} or {"status": "error", "message": "..."}
```

**Indexer:**
```
POST /wazuh/test-indexer/
  → IndexerClient.cluster_health() (tests connectivity + auth)
  → Returns {"status": "ok"} or {"status": "error", "message": "..."}
```

## Migration History

- `0001_initial`: Single WazuhConfiguration with api_type
- `0002_*`: Various data changes
- `0003_*` (current): Removed api_type, added WazuhManagerConfig, dual architecture

## Access Control

- Admin: Full CRUD on configs, test connections, force sync
- Manager: Can view status page and force sync
- L1/L2: No access

## Dependencies

- **accounts:** Role checks (WAZUH_ALLOWED_ROLES)
- **alerts:** Alert model for dedup and creation
