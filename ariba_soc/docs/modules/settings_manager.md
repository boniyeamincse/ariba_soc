# Settings Manager Module

## Purpose

Provides dynamic runtime configuration without code changes or server restarts.

## Key Models

### `SystemSetting`
| Field | Description |
|-------|-------------|
| `key` | Unique identifier (e.g., `SLA_HOURS`) |
| `value` | Stored as string, cast to `data_type` at runtime |
| `data_type` | `str`, `int`, `bool`, `json`, `float` |
| `category` | Grouping: `General`, `Alerts`, `Wazuh`, `SLA`, `Escalation` |
| `description` | Help text |
| `is_active` | Soft-disable settings |

### `SettingAuditLog`
Tracks changes to settings: old_value, new_value, changed_by, timestamp.

## View

### `settings_list` (GET `/settings/`)
Lists all active settings grouped by category.

### `settings_edit` (POST `/settings/<id>/edit/`)
Updates a setting value, validates data_type, creates SettingAuditLog entry.

## Utility Function

```python
def get_setting(key: str, default=None):
    """Fetch and cast a setting value by key."""
    try:
        setting = SystemSetting.objects.get(key=key, is_active=True)
        return setting.get_value()  # Casts based on data_type
    except SystemSetting.DoesNotExist:
        return default
```

## Access Control

- Admin role only

## Dependencies

- None internal
- Used by: all apps via `get_setting()`
