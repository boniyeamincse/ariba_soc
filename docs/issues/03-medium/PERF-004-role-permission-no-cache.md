# PERF-004: RolePermission.has_permission() queries DB every check

**Severity:** Medium  
**Priority:** P2  
**Category:** Performance  
**Status:** Open  
**File:** `ariba_soc/accounts/models.py`

## Current Problem
`has_permission()` executes `RolePermission.objects.get(role=role)` on every permission check. No caching.

## Expected Behavior
Cache `RolePermission` per role using Redis.

## Affected Files
- `ariba_soc/accounts/models.py` (lines 74-80)

## Suggested Fix
```python
from django.core.cache import cache

@staticmethod
def has_permission(role, permission_name):
    cache_key = f'role_perm_{role}'
    perms = cache.get(cache_key)
    if perms is None:
        try:
            role_perm = RolePermission.objects.get(role=role)
            perms = {
                'can_change_severity': role_perm.can_change_severity,
                'can_change_status': role_perm.can_change_status,
                'can_change_verdict': role_perm.can_change_verdict,
                # ... etc
            }
            cache.set(cache_key, perms, 300)  # 5 minutes
        except RolePermission.DoesNotExist:
            return False
    return perms.get(permission_name, False)
```

## QA Verification
- Check Redis for cached role permissions
- Permission checks complete in <1ms
