# API Documentation

## Internal URLs

### Authentication

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/accounts/login/` | LoginView | No | Login page |
| POST | `/accounts/login/` | LoginView | No | Login submission |
| GET | `/accounts/logout/` | LogoutView | Yes | Logout |
| GET | `/accounts/profile/` | profile | Yes | User profile page |

### Dashboard

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/` | dashboard_home | Yes | Main dashboard with stats |
| GET | `/api/severity-breakdown/` | severity_breakdown | Yes | JSON: alert count by severity |
| GET | `/api/daily-trend/` | daily_trend | Yes | JSON: alert count by day |
| GET | `/api/status-distribution/` | status_distribution | Yes | JSON: alert count by status |

### Alerts

| Method | URL | View | Auth Required | Role Required |
|--------|-----|------|---------------|---------------|
| GET | `/alerts/table/` | alert_table | Yes | Any |
| GET | `/alerts/board/` | alert_board | Yes | Any |
| GET | `/alerts/my-alerts/` | my_alerts | Yes | Any |
| GET | `/alerts/<id>/` | alert_detail | Yes | Any |
| POST | `/alerts/<id>/edit/` | edit_alert_ajax | Yes | Any (own or admin) |
| POST | `/alerts/<id>/assign/` | assign_ajax | Yes | Manager/L2/Admin |
| POST | `/alerts/<id>/escalate/` | escalate_ajax | Yes | L1/L2/Manager/Admin |
| POST | `/alerts/<id>/comment/` | add_comment | Yes | Any |

### Wazuh Integration

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/wazuh/status/` | wazuh_status | Yes | Integration status page |
| POST | `/wazuh/manager-config/create/` | manager_config_create | Yes (Admin) | Create Manager config |
| POST | `/wazuh/manager-config/<id>/edit/` | manager_config_update | Yes (Admin) | Edit Manager config |
| POST | `/wazuh/indexer-config/create/` | indexer_config_create | Yes (Admin) | Create Indexer config |
| POST | `/wazuh/indexer-config/<id>/edit/` | indexer_config_update | Yes (Admin) | Edit Indexer config |
| POST | `/wazuh/test-manager/` | test_manager_connection | Yes | Test Manager API |
| POST | `/wazuh/test-indexer/` | test_indexer_connection | Yes | Test Indexer API |
| POST | `/wazuh/sync/` | force_sync | Yes (Admin/Manager) | Trigger alert sync |

### Reports

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/reports/alerts/` | generate_report | Yes (Manager/Admin) | PDF/CSV alert report |
| GET | `/reports/analyst-performance/` | analyst_performance_report | Yes (Manager/Admin) | PDF/CSV performance report |

### Settings

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/settings/` | settings_list | Yes (Admin) | List all settings |
| POST | `/settings/<id>/edit/` | settings_edit | Yes (Admin) | Edit setting |

### Audit

| Method | URL | View | Auth Required | Description |
|--------|-----|------|---------------|-------------|
| GET | `/audit/` | audit_log_view | Yes (Admin) | View audit logs |

## API Response Format

### JSON APIs (Charts)

```json
// GET /api/severity-breakdown/
{
    "labels": ["critical", "high", "medium", "low", "info"],
    "data": [12, 45, 78, 23, 5]
}

// GET /api/daily-trend/
{
    "labels": ["2025-01-01", "2025-01-02", ...],
    "data": [10, 15, ...]
}

// GET /api/status-distribution/
{
    "labels": ["new", "acknowledged", "in_progress", "resolved", "closed", "escalated"],
    "data": [50, 30, 20, 40, 35, 5]
}
```

### AJAX Endpoints

**POST /alerts/<id>/edit/**

Request body: `status=new_status`

Response: `{"success": true}` or `{"success": false, "error": "..."}`

**POST /alerts/<id>/assign/**

Request body: `user_id=123&note=optional`

Response: `{"success": true}` or `{"success": false, "error": "..."}`

### Test Connection Endpoints

**POST /wazuh/test-manager/**

Response: `{"status": "ok", "message": "..."}` or `{"status": "error", "message": "..."}`

**POST /wazuh/test-indexer/**

Response: `{"status": "ok", "message": "..."}` or `{"status": "error", "message": "..."}`

## Wazuh External API Calls

### Manager Client (`ManagerClient`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `authenticate()` | `POST /security/user/authenticate` | Get JWT token |
| `get_alerts(since)` | `GET /security/alerts` | Fetch alerts (paginated) |
| `get_agent_status()` | `GET /agents?status=active` | List active agents |

### Indexer Client (`IndexerClient`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `search(query)` | `POST /wazuh-alerts-*/_search` | OpenSearch query |
| `cluster_health()` | `GET /_cluster/health` | Check cluster status |
