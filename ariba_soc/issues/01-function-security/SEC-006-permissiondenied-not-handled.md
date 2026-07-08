# SEC-006: PermissionDenied 403 Exception Not Gracefully Handled

- **Severity**: Medium
- **Priority**: P1 (this sprint)
- **Category**: Function & Security

## Current Problem
`wazuh_integration/views.py:13-16` raises `PermissionDenied` directly when a user lacks Wazuh access:
```python
def _check_wazuh_access(user):
    role = user.analyst_profile.role
    if role not in ALLOWED_ROLES:
        raise PermissionDenied("You do not have permission to access Wazuh integration.")
```
There is no custom 403 error handler, no `handler403` in urlconf, and no custom 403.html template. Django will serve its default plain-text 403 page, which is unstyled and unhelpful.

## Expected Behavior
A custom `403.html` template (matching the SOC dark theme) should be rendered with a friendly message and a link back to the dashboard.

## Affected Files
- `wazuh_integration/views.py:13-16`
- `config/urls.py` (needs `handler403`)

## Suggested Fix
1. Create `templates/403.html`:
```html
{% extends 'base.html' %}
{% block content %}
<div class="container text-center py-5">
    <i class="bi bi-shield-exclamation" style="font-size: 4rem; color: var(--severity-critical);"></i>
    <h3 class="mt-3">Access Denied</h3>
    <p class="text-muted">{{ exception|default:"You don't have permission to access this page." }}</p>
    <a href="{% url 'alerts:table' %}" class="btn btn-ariba-primary">Back to Dashboard</a>
</div>
{% endblock %}
```
2. Add to `config/urls.py`: `handler403 = 'alerts.views.handler403'`
3. Create a simple `handler403` view that renders the template.

## QA Verification
1. Log in as L1_analyst, navigate to `/wazuh/agents/` → must see styled 403 page, not Django default plain page.
