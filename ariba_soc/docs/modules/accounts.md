# Accounts Module

## Purpose

Handles user authentication, profiles, and role-based access control.

## Key Models

### `AnalystProfile`
- **OneToOneField → User:** Links to Django's built-in User model
- **role:** CharField with choices: `admin`, `manager`, `l2_analyst`, `l1_analyst`
- **phone, avatar:** Optional contact info
- Auto-created via signal on User creation

### `ROLE_CHOICES`
```python
ROLE_CHOICES = [
    ('admin', 'Administrator'),
    ('manager', 'Manager'),
    ('l2_analyst', 'L2 Analyst'),
    ('l1_analyst', 'L1 Analyst'),
]
```

### `WAZUH_ALLOWED_ROLES`
```python
WAZUH_ALLOWED_ROLES = ['admin', 'manager']
```
Used to gate access to Wazuh configuration pages.

## Key Views

- `profile` — View/edit own profile
- User management via Django admin only (no custom user management views)

## Key Decorator

### `@role_required(*roles)`
```python
@role_required('admin', 'manager')
def sensitive_view(request):
    ...
```
Returns 403 if user's role is not in the allowed list.

## Signals

- `create_analyst_profile` — post_save on User: creates AnalystProfile; superusers get role='admin'

## Tests

Basic auth tests in `accounts/tests.py`.

## Dependencies

- None internal (uses Django auth only)
- Used by: alerts, audit, dashboard, reports, wazuh_integration
