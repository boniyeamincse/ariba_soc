# SEC-003: No rate limiting on login

**Severity:** High  
**Priority:** P1  
**Category:** Security (Brute Force)  
**Status:** Open  
**File:** `ariba_soc/accounts/urls.py`

## Current Problem
The login view uses Django's built-in `LoginView` with no rate limiting, CAPTCHA, or account lockout. An attacker can brute-force credentials without throttling.

## Expected Behavior
- Rate limit: 5 login attempts per minute per IP
- Account lockout after 10 failed attempts
- CAPTCHA after 3 failed attempts

## Affected Files
- `ariba_soc/accounts/urls.py` (line 8)
- `ariba_soc/accounts/views.py`

## Suggested Fix
```bash
pip install django-axes
```
```python
# settings.py
INSTALLED_APPS += ['axes']
MIDDLEWARE += ['axes.middleware.AxesMiddleware']

# axes config
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
```

## QA Verification
- Attempt 5 logins with wrong password → account locked
- Wait 15 minutes → account unlocked
