# Authentication & Authorization

## Authentication

Ariba SOC uses Django's built-in authentication system with session-based auth.

### Login Flow

1. User navigates to `/accounts/login/`
2. Submits username + password
3. Django authenticates against the database
4. On success: session created, redirected to dashboard
5. On failure: error message returned

### Logout

GET `/accounts/logout/` — clears session, redirects to login.

### Session Configuration

- Session engine: database-backed (default)
- Session expiry: browser session (closes on browser exit)
- CSRF protection: enabled globally
- Login required: enforced via `@login_required` on all views

## Role-Based Access Control (RBAC)

### Role Hierarchy

```
Administrator (admin)     → Full system access
       ↑
Manager (manager)         → Reports, assign, settings (read-only)
       ↑
L2 Analyst (l2_analyst)   → Full alert triage, investigate, resolve
       ↑
L1 Analyst (l1_analyst)   → View alerts, acknowledge, escalate
```

### Implementation

Roles are stored in `AnalystProfile.role` (not Django groups/permissions).

#### `@role_required` Decorator

```python
from accounts.decorators import role_required

@role_required('admin', 'manager')
def some_view(request):
    ...
```

If user lacks required role: returns 403 Forbidden.

#### Template-Level Checks

```django
{% if user.analystprofile.role == 'admin' %}
  <a href="/admin/">Admin Panel</a>
{% endif %}
```

Utility conditions in base template:
```django
{% if user.analystprofile.role in 'admin,manager' %}
  {# show manager-level items #}
{% endif %}
```

### Permission Matrix

| Action | L1 | L2 | Manager | Admin |
|--------|----|----|---------|-------|
| View dashboard | ✅ | ✅ | ✅ | ✅ |
| View alert table | ✅ | ✅ | ✅ | ✅ |
| View alert detail | ✅ | ✅ | ✅ | ✅ |
| View alert board | ✅ | ✅ | ✅ | ✅ |
| View my alerts | ✅ | ✅ | ✅ | ✅ |
| Change alert status | Own only | Any | Any | Any |
| Assign alerts | ❌ | ✅ | ✅ | ✅ |
| Escalate alerts | ✅ | ✅ | ❌ | ❌ |
| Add comments | ✅ | ✅ | ✅ | ✅ |
| View reports | ❌ | ❌ | ✅ | ✅ |
| Generate reports | ❌ | ❌ | ✅ | ✅ |
| Manage settings | ❌ | ❌ | ❌ | ✅ |
| View audit logs | ❌ | ❌ | ❌ | ✅ |
| Manage Wazuh config | ❌ | ❌ | ❌ | ✅ |
| Force sync alerts | ❌ | ❌ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ✅ |

### Superuser Auto-Configuration

On user creation (via signal): superusers automatically get `AnalystProfile` with `role='admin'`.

## Allowed Roles for Wazuh Access

Defined in `accounts/models.py`:

```python
WAZUH_ALLOWED_ROLES = ['admin', 'manager']
```

Only users with these roles can access Wazuh configuration pages and trigger sync.
