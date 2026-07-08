# WZ-004: No Wazuh API Health Check / Status Probe

- **Severity**: Low
- **Priority**: P3 (backlog)
- **Category**: Wazuh API

## Current Problem
The Wazuh integration has no dedicated health-check endpoint that can be used by:
- Monitoring systems (Prometheus, Nagios)
- Kubernetes liveness/readiness probes
- Load balancers
- The UI itself (to show connection status at a glance)

The `wazuh_status` view (`wazuh_integration/views.py:20-34`) renders the status page but performs no live connectivity check. The `wazuh_agents` view (`wazuh_integration/views.py:56-72`) tests connectivity but only as a side effect of fetching agents.

## Expected Behavior
A dedicated `/wazuh/health/` endpoint should:
1. Attempt to authenticate with the Wazuh API
2. Return JSON `{"status": "ok"}` or `{"status": "error", "detail": "..."}` 
3. Return HTTP 200 if healthy, 503 if not

## Affected Files
- `wazuh_integration/views.py` (needs new health view)
- `wazuh_integration/urls.py` (needs new route)

## Suggested Fix
```python
@login_required
def wazuh_health(request):
    try:
        client = WazuhClient()
        token = client.authenticate()
        if token:
            return JsonResponse({'status': 'ok', 'api_url': client.base_url})
        return JsonResponse({'status': 'error', 'detail': 'Authentication failed'}, status=503)
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)
```
Add URL: `path('health/', views.wazuh_health, name='health')`

## QA Verification
1. With Wazuh API configured correctly: `GET /wazuh/health/` → `{"status": "ok"}` + 200
2. With wrong credentials: `GET /wazuh/health/` → `{"status": "error", ...}` + 503
3. Without any configuration: `GET /wazuh/health/` → `{"status": "error", ...}` + 503
