# SEC-007: No Content-Security-Policy header

**Severity:** High  
**Priority:** P1  
**Category:** Security (XSS)  
**Status:** Open  
**File:** `ariba_soc/config/settings.py`

## Current Problem
The app loads Bootstrap, Chart.js from CDN but has no CSP header. If an attacker injects `<script>`, there's no CSP to block it.

## Expected Behavior
CSP header blocks inline scripts and only allows trusted domains.

## Affected Files
- `ariba_soc/config/settings.py` (missing CSP config)

## Suggested Fix
```bash
pip install django-csp
```
```python
# settings.py
INSTALLED_APPS += ['csp']
MIDDLEWARE += ['csp.middleware.CSPMiddleware']

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "cdn.jsdelivr.net")
CSP_STYLE_SRC = ("'self'", "cdn.jsdelivr.net", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "cdn.jsdelivr.net")
CSP_FONT_SRC = ("'self'", "cdn.jsdelivr.net")
```

## QA Verification
- Check response headers for `Content-Security-Policy`
- Inject `<script>alert(1)</script>` → blocked by CSP
