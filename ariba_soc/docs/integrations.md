# Integrations

## Wazuh Manager Integration

### Overview

Ariba SOC connects to the Wazuh Manager via its REST API on port `55000`. Authentication is JWT-based.

### Kali Agent Connectivity Best Practice

If your Kali host runs the Wazuh agent and the Wazuh manager is on the same Docker host, use the loopback address. Do not hardcode a LAN, Wi-Fi, or public IP for the manager in that case.

Recommended agent config for the Kali host:

```xml
<client>
  <server>
    <address>127.0.0.1</address>
    <port>1514</port>
    <protocol>tcp</protocol>
  </server>

  <config-profile>kali, kali-host, linux</config-profile>
  <notify_time>10</notify_time>
  <time-reconnect>60</time-reconnect>
  <auto_restart>yes</auto_restart>
</client>
```

Why this is the right choice in a same-host Docker lab:

- `127.0.0.1` stays stable when the machine changes from Wi-Fi to LAN.
- Docker publishes the manager port to the host in `infrastructure/docker-compose.yml`.
- `tcp` plus `time-reconnect` and `auto_restart` helps the agent recover after the network briefly drops.

What this does not solve:

- If the machine is offline, the agent cannot stay connected in real time.
- If the manager is on another host, use a stable DNS name or a VPN address such as WireGuard or Tailscale instead of a raw IP.

See the dedicated setup guide: [Kali Agent Setup](guide/kali-agent-setup.md)

### Configuration

Configured via UI (Admin → Wazuh Integration → Manager Config):

| Field | Example Value | Description |
|-------|---------------|-------------|
| Name | `Production Wazuh` | Config label |
| API URL | `https://10.24.66.2:55000` | Manager API base URL |
| Username | `soc-api-user` | Wazuh API user |
| Password | `Care@#$1718` | Wazuh API password |
| Is Active | ✅ | Enable this config |

Or via environment variables (`.env`):
```ini
WAZUH_MANAGER_URL=https://10.24.66.2:55000
WAZUH_MANAGER_USER=soc-api-user
WAZUH_MANAGER_PASSWORD=Care@#$1718
```

### Manager User Requirements

The Wazuh API user must have:
- **Role:** `administrator` (id=1) for full API access
- **Role:** `agents_readonly` (id=4) for agent queries

These roles are assigned directly in Wazuh's RBAC SQLite database (`/var/ossec/api/configuration/rbac/rbac.db`).

### API Calls

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/security/user/authenticate` | POST | Get JWT token (basic auth) |
| `/security/alerts` | GET | Fetch alerts with pagination |
| `/agents?status=active` | GET | List active agents |

### Client Implementation

```python
# wazuh_integration/services.py

class ManagerClient:
    def __init__(self, config: WazuhManagerConfig):
        self.config = config
        self.base_url = config.api_url.rstrip('/')
        self.token = None

    def authenticate(self) -> str:
        """Get JWT token using Basic Auth."""
        response = requests.post(
            f'{self.base_url}/security/user/authenticate',
            auth=(self.config.username, self.config.password),
            verify=False
        )
        self.token = response.json()['data']['token']
        return self.token

    def get_alerts(self, since: str = None, limit: int = 500) -> list:
        """Fetch paginated alerts."""
        ...
```

## Wazuh Indexer (OpenSearch) Integration

### Overview

Ariba SOC connects to the Wazuth Indexer (OpenSearch) API on port `9200`. Authentication is HTTP Basic Auth.

### Configuration

Configured via UI (Admin → Wazuh Integration → Indexer Config):

| Field | Example Value | Description |
|-------|---------------|-------------|
| Name | `Production Indexer` | Config label |
| API URL | `https://10.24.66.2:9200` | Indexer API base URL |
| Username | `ariba-soc-reader` | OpenSearch user |
| Password | `AribaS0C_AlertReader!@#` | OpenSearch password |
| Verify SSL | ❌ | Disable for self-signed certs |
| Is Active | ✅ | Enable this config |

### Indexer User Setup

The OpenSearch user was created with a dedicated role:

```
Role: ariba_soc_alert_reader
- Cluster permissions: cluster_composite_ops
- Index permissions: wazuh-alerts-* → READ, SEARCH
```

Applied via OpenSearch Security REST API:
```bash
curl -k -u admin:password \
  -X PUT "https://localhost:9200/_plugins/_security/api/roles/ariba_soc_alert_reader" \
  -H "Content-Type: application/json" \
  -d '{
    "cluster_permissions": ["cluster_composite_ops"],
    "index_permissions": [{
      "index_patterns": ["wazuh-alerts-*"],
      "allowed_actions": ["read", "search"]
    }]
  }'

curl -k -u admin:password \
  -X PUT "https://localhost:9200/_plugins/_security/api/internalusers/ariba-soc-reader" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "AribaS0C_AlertReader!@#",
    "backend_roles": ["ariba_soc_alert_reader"]
  }'
```

### API Calls

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/wazuh-alerts-*/_search` | POST | Query alerts via OpenSearch DSL |
| `/_cluster/health` | GET | Cluster health check |

### Client Implementation

```python
class IndexerClient:
    def __init__(self, config: WazuhConfiguration):
        self.config = config
        self.base_url = config.api_url.rstrip('/')
        self.auth = (config.username, config.password)

    def search(self, query: dict) -> dict:
        """Execute an OpenSearch query."""
        response = requests.post(
            f'{self.base_url}/wazuh-alerts-*/_search',
            json=query,
            auth=self.auth,
            verify=self.config.verify_ssl
        )
        return response.json()
```

## Sync Flow

```
force_sync() or scheduled task
    │
    ├── ManagerClient.get_alerts(since=last_sync)
    │       │
    │       └── Paginated fetch from Wazuh Manager
    │
    ├── For each alert:
    │       ├── Check dedup by wazuh_alert_id
    │       ├── Create Alert if new
    │       └── Parse fields (severity, title, agent, etc.)
    │
    ├── ManagerClient.get_agent_status()
    │
    └── Create WazuhSyncLog record
```

## Testing Connections

Both integrations have dedicated test endpoints:

1. **Manager:** POST `/wazuh/test-manager/` — authenticates and fetches agent list
2. **Indexer:** POST `/wazuh/test-indexer/` — checks cluster health

Both return `{"status": "ok"}` on success.
