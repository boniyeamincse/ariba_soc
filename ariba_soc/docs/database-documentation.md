# Database Documentation

## Entity-Relationship Overview

```
User (Django auth) ──1:1── AnalystProfile
User ──1:N── Alert (assigned_to)
User ──1:N── AlertComment (author)
User ──1:N── AlertAuditLog (actor)
User ──1:N── Notification (recipient)
User ──1:N── AuditLog (actor)
User ──1:N── WazuhSyncLog (triggered_by)

Alert ──1:N── AlertComment
Alert ──1:N── AlertAuditLog
Alert ──1:N── Notification
Alert ──N:1── AlertSource (optional)
Alert ──1:1── Wazuh Alert (via wazuh_alert_id)

SystemSetting ──1:N── SettingAuditLog
```

## Tables

### `accounts_analystprofile`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `user_id` | OneToOneField(User) | FK, unique, not null | Links to Django user |
| `role` | CharField(20) | choices=ROLE_CHOICES | `admin`, `manager`, `l2_analyst`, `l1_analyst` |
| `phone` | CharField(20) | nullable | Contact number |
| `avatar` | ImageField | nullable | Profile picture |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**ROLE_CHOICES:** `admin` (Administrator), `manager` (Manager), `l2_analyst` (L2 Analyst), `l1_analyst` (L1 Analyst)

### `alerts_alert`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `wazuh_alert_id` | CharField(255) | unique, nullable | Wazuh alert ID for dedup |
| `rule_id` | CharField(50) | indexed | Wazuh rule ID |
| `rule_description` | TextField | | Alert description |
| `severity` | CharField(20) | choices | `critical`, `high`, `medium`, `low`, `info` |
| `status` | CharField(20) | choices, indexed | `new`, `acknowledged`, `in_progress`, `resolved`, `closed`, `escalated` |
| `source` | CharField(255) | nullable | Alert source name |
| `source_ip` | GenericIPAddressField | nullable | Originating IP |
| `agent_id` | CharField(50) | indexed | Wazuh agent ID |
| `agent_name` | CharField(255) | nullable | Wazuh agent name |
| `title` | CharField(512) | | Alert title |
| `description` | TextField | nullable | Full description |
| `assigned_to_id` | ForeignKey(User) | FK, nullable, indexed | Current assignee |
| `escalated_to_id` | ForeignKey(User) | FK, nullable | Escalation target |
| `escalation_note` | TextField | nullable | Reason for escalation |
| `acknowledged_at` | DateTimeField | nullable | When acknowledged |
| `resolved_at` | DateTimeField | nullable | When resolved |
| `raw_data` | JSONField | nullable | Original Wazuh alert JSON |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

**Status choices:** `new`, `acknowledged`, `in_progress`, `resolved`, `closed`, `escalated`

**Indexes:** `severity`, `status`, `agent_id`, `rule_id`, `assigned_to_id`, `created_at`, `wazuh_alert_id` (unique)

### `alerts_alertcomment`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `alert_id` | ForeignKey(Alert) | FK, CASCADE | Related alert |
| `author_id` | ForeignKey(User) | FK | Comment author |
| `content` | TextField | | Comment text |
| `created_at` | DateTimeField | auto_now_add | |

### `alerts_alertauditlog`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `alert_id` | ForeignKey(Alert) | FK, CASCADE | Related alert |
| `actor_id` | ForeignKey(User) | FK, nullable | Who performed action |
| `action` | CharField(50) | | e.g., `status_change`, `assignment` |
| `old_value` | TextField | nullable | Previous value |
| `new_value` | TextField | nullable | New value |
| `timestamp` | DateTimeField | auto_now_add | |

### `alerts_notification`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `alert_id` | ForeignKey(Alert) | FK, CASCADE | Related alert |
| `recipient_id` | ForeignKey(User) | FK | Target user |
| `notification_type` | CharField(50) | | `assignment`, `escalation`, `status_change` |
| `message` | TextField | | Notification text |
| `is_read` | BooleanField | default=False | Read status |
| `created_at` | DateTimeField | auto_now_add | |

### `audit_auditlog`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `actor_id` | ForeignKey(User) | FK, nullable | User who performed action |
| `action` | CharField(50) | choices | `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, etc. |
| `model_name` | CharField(100) | | Model affected |
| `object_id` | CharField(100) | nullable | Object PK |
| `details` | JSONField | nullable | Change details |
| `ip_address` | GenericIPAddressField | nullable | Request IP |
| `timestamp` | DateTimeField | auto_now_add | |

### `settings_manager_systemsetting`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `key` | CharField(100) | unique | Setting identifier |
| `value` | TextField | | Setting value |
| `data_type` | CharField(20) | default='str' | `str`, `int`, `bool`, `json`, `float` |
| `category` | CharField(50) | default='General' | Grouping category |
| `description` | TextField | nullable | Help text |
| `is_active` | BooleanField | default=True | |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

### `wazuh_integration_wazuhmanagerconfig`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `name` | CharField(100) | | Config name |
| `api_url` | URLField | | Manager API base URL |
| `username` | CharField(255) | | API username |
| `password` | CharField(255) | | API password |
| `is_active` | BooleanField | default=False | |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

### `wazuh_integration_wazuhconfiguration`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `name` | CharField(100) | | Config name |
| `api_url` | URLField | | Indexer API base URL |
| `username` | CharField(255) | | OpenSearch username |
| `password` | CharField(255) | | OpenSearch password |
| `verify_ssl` | BooleanField | default=False | |
| `is_active` | BooleanField | default=False | |
| `created_at` | DateTimeField | auto_now_add | |
| `updated_at` | DateTimeField | auto_now | |

### `wazuh_integration_wazuhsynclog`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | BigAutoField | PK | |
| `triggered_by_id` | ForeignKey(User) | FK, nullable | Who triggered sync |
| `status` | CharField(20) | | `success`, `failed`, `partial` |
| `alerts_fetched` | IntegerField | default=0 | |
| `alerts_created` | IntegerField | default=0 | |
| `alerts_skipped` | IntegerField | default=0 | Duplicates skipped |
| `error_message` | TextField | nullable | Error details |
| `started_at` | DateTimeField | | |
| `completed_at` | DateTimeField | nullable | |

## Migrations

Current migration state: `wazuh_integration` has `0003_*` (dual architecture migration removing single `api_type`).

Run migrations with:

```bash
python manage.py migrate
python manage.py showmigrations  # Check status
```

## Index Strategy

- **Frequently filtered columns:** `severity`, `status`, `agent_id`, `rule_id`, `assigned_to_id`, `created_at` — all indexed.
- **Unique constraints:** `wazuh_alert_id` on `alerts_alert` for dedup; `key` on `systemsetting`.
- **Foreign keys:** All FK columns indexed by Django default.
