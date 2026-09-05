# RBAC-003: Settings Role Filter Hardcoded Without DB Override

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: RBAC

## Current Problem
`alerts/context_processors.py:11` defines `settings_roles` as a hardcoded Python list:
```python
'settings_roles': ['SOC_MGR', 'SOC_ENG', 'ADMIN'],
```
This value is also duplicated in `settings_manager/views.py:20`:
```python
ALLOWED_SETTINGS_ROLES = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
```
The Settings megamenu visibility in `base.html:34` depends on this context variable. There is no way for a superuser to grant Settings access to a different role without editing Python code.

## Expected Behavior
The list of roles allowed to access Settings should be stored in the `SystemSetting` model (key: `settings_allowed_roles`). The context processor should read from the database, falling back to the hardcoded list if not configured.

## Affected Files
- `alerts/context_processors.py:11`
- `settings_manager/views.py:20`

## Suggested Fix
```python
# context_processors.py
from settings_manager.models import SystemSetting

def user_alerts_context(request):
    ...
    stored = SystemSetting.get_setting('settings_allowed_roles', '')
    if stored:
        roles = [r.strip() for r in stored.split(',')]
    else:
        roles = ['SOC_MGR', 'SOC_ENG', 'ADMIN']
    return {
        ...
        'settings_roles': roles,
    }
```

## QA Verification
1. Create system setting with key `settings_allowed_roles` value `L1,L2,SOC_ENG,SOC_MGR,ADMIN`.
2. Log in as L1 analyst — the Settings menu must now appear in the navbar.
3. Delete the setting — L1 must no longer see the Settings menu.
