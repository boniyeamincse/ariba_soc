# RBAC-002: Role Enum Mismatch Between Accounts and Settings

- **Severity**: Medium
- **Priority**: P1 (this sprint)
- **Category**: RBAC

## Current Problem
Role checks are inconsistently defined across the codebase:
- `accounts/models.py:7-13` defines: `L1, L2, SOC_ENG, SOC_MGR, ADMIN, VIEWER`
- `alerts/context_processors.py:11` hardcodes: `['SOC_MGR', 'SOC_ENG', 'ADMIN']` for settings access
- `settings_manager/views.py:20` hardcodes: `['SOC_MGR', 'SOC_ENG', 'ADMIN']`
- `wazuh_integration/views.py:10` defines: `['ADMIN', 'SOC_ENG', 'SOC_MGR', 'L1', 'L2']`

If a new role is added (e.g., `SOC_LEAD`), it must be added to 4 separate places. The hardcoded string lists are not DRY and are prone to inconsistency.

## Expected Behavior
Role permission lists should be defined in a single location (`accounts/models.py`) as constants or class properties, and imported everywhere else.

## Affected Files
- `accounts/models.py` (should export `SETTINGS_ROLES`, `WAZUH_ROLES`, etc.)
- `alerts/context_processors.py:11`
- `settings_manager/views.py:20`
- `wazuh_integration/views.py:10`

## Suggested Fix
In `accounts/models.py`:
```python
SETTINGS_ALLOWED_ROLES = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
WAZUH_ALLOWED_ROLES = ['ADMIN', 'SOC_ENG', 'SOC_MGR', 'L1', 'L2']
```

Then import:
```python
from accounts.models import SETTINGS_ALLOWED_ROLES, WAZUH_ALLOWED_ROLES
```

## QA Verification
1. After refactoring, all role-gated functionality must work identically.
2. Adding a new role to `SETTINGS_ALLOWED_ROLES` in `accounts/models.py` must immediately grant settings access.
