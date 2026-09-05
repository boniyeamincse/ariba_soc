# API Reference

## Wazuh Manager API

Base URL: `https://wazuh.manager:55000`

### Authentication
```bash
TOKEN=$(curl -k -u admin:password \
  https://wazuh.manager:55000/security/user/authenticate | jq -r '.data.token')
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all agents |
| GET | `/agents/{agent_id}` | Get agent details |
| GET | `/manager/status` | Manager status |
| GET | `/rules` | List detection rules |
| GET | `/alerts` | List alerts |

### Example: List Agents
```bash
curl -k -H "Authorization: Bearer $TOKEN" \
  https://wazuh.manager:55000/agents?limit=500
```

## Wazuh Indexer API

Base URL: `https://wazuh.indexer:9200`

### Authentication
```bash
curl -k -u admin:password https://wazuh.indexer:9200/_cluster/health
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/_cluster/health` | Cluster health status |
| GET | `/_cat/indices` | List all indices |
| POST | `/{index}/_search` | Search alerts |

### Example: Fetch Recent Alerts
```bash
curl -k -u admin:password \
  -X POST "https://wazuh.indexer:9200/wazuh-alerts-*/_search" \
  -H "Content-Type: application/json" \
  -d '{"size": 100, "sort": [{"timestamp": {"order": "desc"}}]}'
```

## Ariba SOC Internal API

### Alert Sync
```bash
# Trigger manual sync
docker compose exec web python manage.py wazuh_sync --time-range 1h
```

### Management Commands

| Command | Description |
|---------|-------------|
| `wazuh_sync` | Sync alerts from Wazuh Indexer |
| `cleanup_audit_logs` | Clean old audit logs |
| `generate_reports` | Generate scheduled reports |
| `seed_wazuh_config` | Seed Wazuh connection config |

## Python Client

### Wazuh Manager
```python
from wazuh_integration.services import ManagerClient
from wazuh_integration.models import WazuhManagerConfig

config = WazuhManagerConfig.objects.first()
client = ManagerClient(config)
client.authenticate()

agents = client.fetch_agents()
status = client.get_manager_status()
```

### Wazuh Indexer
```python
from wazuh_integration.services import IndexerClient
from wazuh_integration.models import WazuhConfiguration

config = WazuhConfiguration.objects.first()
client = IndexerClient(config)

# Test connection
health = client.test_connection()

# Fetch alerts
alerts = client.fetch_alerts(time_range='1h', max_alerts=5000)
```

## Webhook Integration

Ariba SOC can receive alerts via webhook:

```bash
curl -X POST http://localhost:8080/api/alerts/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "alert_name": "Test Alert",
    "severity": "High",
    "source": "External SIEM",
    "description": "Suspicious activity detected"
  }'
```

## Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| Login | 5 attempts | 15 minutes |
| API (authenticated) | 1000 requests | 1 minute |
| Webhook | 100 requests | 1 minute |

## Error Responses

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Rate Limited |
| 500 | Internal Server Error |
