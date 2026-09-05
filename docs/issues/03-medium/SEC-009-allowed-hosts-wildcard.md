# SEC-009: ALLOWED_HOSTS = * in production

**Severity:** Medium  
**Priority:** P2  
**Category:** Security  
**Status:** Open  
**File:** `ariba_soc/config/settings.py`

## Current Problem
Default `DJANGO_ALLOWED_HOSTS` is `*`, allowing Host header injection in production.

## Expected Behavior
Production requires specific domain. Startup check if `DEBUG=False` and `ALLOWED_HOSTS` contains `*`.

## Affected Files
- `ariba_soc/config/settings.py` (line 24)

## Suggested Fix
```python
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

if not DEBUG and '*' in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS must not contain * when DEBUG=False'
    )
```

## QA Verification
- Set `DEBUG=False` and `ALLOWED_HOSTS=*` → app refuses to start
- Set specific domain → app starts normally
