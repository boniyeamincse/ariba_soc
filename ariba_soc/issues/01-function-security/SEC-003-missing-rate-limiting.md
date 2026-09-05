# SEC-003: No Rate Limiting on Authentication or API Endpoints

- **Severity**: High
- **Priority**: P1 (this sprint)
- **Category**: Function & Security

## Current Problem
No view in the application applies Django's `@ratelimit` decorator or any other rate-limiting mechanism. Specifically:
- Login endpoint (`accounts/urls.py:8`) is unprotected — brute-force attacks possible
- `alerts_api` and `alert_move_api` (`alerts/views.py:254,279`) have no rate limits
- Alert CSV/Excel export endpoints (`reports/views.py:32,47`) can be hammered

## Expected Behavior
Login attempts should be limited to ~5 per minute per IP. API endpoints should have reasonable rate limits to prevent abuse.

## Affected Files
- `accounts/urls.py:8` (login view)
- `alerts/views.py:254-274` (alerts_api)
- `alerts/views.py:277-291` (alert_move_api)
- `reports/views.py:32-44` (export_csv)
- `reports/views.py:47-65` (export_excel)

## Suggested Fix
Add `django-ratelimit` to requirements and apply decorators:
```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', method='POST')
def login_view(request): ...

@ratelimit(key='ip', rate='30/m')
def alerts_api(request): ...
```

Or implement custom middleware-based rate limiting.

## QA Verification
1. Send 6+ rapid POST requests to login — the 6th must return 429 or throttle response.
2. Send 35+ requests to `/api/alerts/` in one minute — verify throttling kicks in.
