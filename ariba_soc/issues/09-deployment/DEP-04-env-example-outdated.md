# DEP-04: .env.example Missing Required Variables

- **Severity**: Medium
- **Priority**: P2 (next sprint)
- **Category**: Deployment

## Current Problem
The `.env.example` file (`manage.py` sibling) is incomplete. Based on the settings and application code, it's missing several environment variables:
- Missing: `WAZUH_API_URL`, `WAZUH_API_USERNAME`, `WAZUH_API_PASSWORD`, `WAZUH_VERIFY_SSL`, `WAZUH_API_TIMEOUT` (used in `config/settings.py:110-114`)
- Missing: `REDIS_URL` (needed for caching)
- Missing: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` (controlled by `DEBUG`)
- No descriptions or example values for each variable

## Expected Behavior
`.env.example` should include ALL environment variables that `settings.py` reads, with example values and descriptions.

## Affected Files
- `.env.example` (needs to be updated)

## Suggested Fix
```bash
# Django Core
DJANGO_SECRET_KEY=change-me-to-a-long-random-string
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=.example.com,localhost
DJANGO_RUN_MODE=production

# Database (PostgreSQL)
DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=ariba_soc
DATABASE_USER=ariba_soc
DATABASE_PASSWORD=strong-db-password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Wazuh API
WAZUH_API_URL=https://wazuh-manager:55000
WAZUH_API_USERNAME=wazuh-api-user
WAZUH_API_PASSWORD=wazuh-api-password
WAZUH_VERIFY_SSL=False
WAZUH_API_TIMEOUT=30

# Redis (for caching)
REDIS_URL=redis://localhost:6379/1

# Email (for notifications)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=notifications@example.com
EMAIL_HOST_PASSWORD=smtp-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@example.com
```

## QA Verification
1. Copy `.env.example` to `.env`.
2. Set all variables to valid values.
3. Run the app — it must read all variables without errors.
