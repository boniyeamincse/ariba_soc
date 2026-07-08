# SEC-001: Hardcoded Fallback Secret Key in Production

- **Severity**: Critical
- **Priority**: P0 (immediate)
- **Category**: Function & Security

## Current Problem
`config/settings.py:7` uses a fallback dev secret key when `DJANGO_SECRET_KEY` is not set:
```python
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-secret-key-change-in-production')
```
If deployed without setting the env var, Django uses a known string for cryptographic signing (sessions, CSRF, password reset tokens). An attacker who knows this key can forge session cookies and perform CSRF attacks.

## Expected Behavior
The application must **fail hard** at startup if `DJANGO_SECRET_KEY` is not set in production. No fallback should be used, or the fallback must be randomized per-instance.

## Affected Files
- `config/settings.py:7`

## Suggested Fix
```python
import sys
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY and not DEBUG:
    print("FATAL: DJANGO_SECRET_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)
if not SECRET_KEY:
    SECRET_KEY = 'dev-secret-key-change-in-production'
```

Or use `django.core.management.utils.get_random_secret_key()` as a dev-only fallback.

## QA Verification
1. Unset `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=False`, restart → app must exit with error message.
2. Unset `DJANGO_SECRET_KEY`, set `DJANGO_DEBUG=True`, restart → app must start (dev mode).
3. Set `DJANGO_SECRET_KEY` to a custom value, restart → session signing must use the new key.
