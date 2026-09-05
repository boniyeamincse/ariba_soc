# SEC-007: No CSRF Exemptions but Missing Token on Some POST Paths

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Function & Security

## Current Problem
Most POST endpoints use `@require_POST` or check `request.method == 'POST'` but rely on the global CSRF middleware. The `alert_move_api` (`alerts/views.py:279`) reads JSON from `request.body` using `json.loads(request.body)`. If the frontend sends a POST with `Content-Type: application/json` without including the CSRF token in headers, Django's CSRF middleware will reject it. This is currently unprotected because **no view explicitly exempts CSRF** — but if the frontend already includes the token in headers, it works. The issue is inconsistent handling.

Additionally:
- `alerts/views.py:279` uses `json.loads(request.body)` without CSRF token validation on the client side for the board drag-and-drop
- No views use `@csrf_exempt` (correct), but no views use `@csrf_protect` either (redundant but explicit)

## Expected Behavior
- The `alert_move_api` should support CSRF token via `X-CSRFToken` header (standard Django JS pattern)
- The board's drag-and-drop JS must include the CSRF token in the request headers

## Affected Files
- `alerts/views.py:277-291` (alert_move_api)
- `templates/ariba_soc/alert_board.html` (frontend JS for drag-and-drop)

## Suggested Fix
In the board template's JS:
```javascript
fetch(`/api/alerts/${alertId}/move/`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({status: newStatus}),
})
```

## QA Verification
1. Drag an alert card to a new column on the board page — must return 200, not 403.
2. Inspect browser network tab — the POST must include `X-CSRFToken` header.
