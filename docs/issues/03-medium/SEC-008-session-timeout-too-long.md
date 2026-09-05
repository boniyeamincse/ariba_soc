# SEC-008: Session timeout too long for SOC

**Severity:** Medium  
**Priority:** P2  
**Category:** Security (Session Management)  
**Status:** Open  
**File:** `ariba_soc/config/settings.py`

## Current Problem
No `SESSION_COOKIE_AGE` set. Django defaults to 2 weeks, which is too long for a SOC tool with access to sensitive security data.

## Expected Behavior
- Session timeout: 1 hour
- Session expires on browser close

## Affected Files
- `ariba_soc/config/settings.py`

## Suggested Fix
```python
# SOC-specific session settings
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # Reset timer on activity
```

## QA Verification
- Login → wait 1 hour → session expired
- Login → close browser → session expired on reopen
