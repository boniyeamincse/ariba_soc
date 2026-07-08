# DEP-02: Missing requirements.txt

- **Severity**: Critical
- **Priority**: P0 (immediate)
- **Category**: Deployment

## Current Problem
The project has no `requirements.txt` or `pyproject.toml`. All dependencies are installed globally on the development machine. When deploying to a new environment, there is no documented list of packages to install.

Based on imports across the codebase, the required packages include (at minimum):
- Django >= 5.0
- psycopg2-binary (for PostgreSQL)
- requests (for Wazuh API)
- openpyxl (for Excel export)
- gunicorn (for production WSGI)
- django-cryptography (for encrypted fields — optional but recommended)
- redis (for caching — optional)
- django-ratelimit (for rate limiting — optional)

## Expected Behavior
A complete `requirements.txt` should be generated with pinned versions (at least major.minor) and included in the repository.

## Affected Files
- `requirements.txt` (needs to be created)

## Suggested Fix
```txt
Django>=5.0,<5.1
psycopg2-binary>=2.9
requests>=2.31
openpyxl>=3.1
gunicorn>=21.2
python-decouple>=3.8
django-cryptography>=1.1
redis>=5.0
django-ratelimit>=4.1
```
Also create a `requirements-dev.txt`:
```txt
-r requirements.txt
django-debug-toolbar>=4.2
ipython>=8.0
```

## QA Verification
1. Create a fresh Python venv: `python -m venv test-env && source test-env/bin/activate`
2. Run `pip install -r requirements.txt` — must install without errors.
3. Run `python manage.py runserver` — must start successfully.
